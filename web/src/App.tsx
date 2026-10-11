import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Direction,
  Position,
  GameStatus,
  Question,
  AnswerResult,
  GameStats,
  AppScreen,
  User,
  UserStats,
  CategoryFilter,
  Match,
} from "./types";
import { soundEffects } from "./services/audioService";
import { authService } from "./services/authService";
import { matchService } from "./services/matchService";
import { progressService } from "./services/progressService";
import { Header } from "./components/Header";
import { GameBoard } from "./components/GameBoard";
import { QuestionModal } from "./components/QuestionModal";
import { DpadControls } from "./components/DpadControls";
import { OverlayScreen } from "./components/OverlayScreen";
import { LoginScreen } from "./components/LoginScreen";
import { HomeScreen } from "./components/HomeScreen";
import { CategoriesScreen } from "./components/CategoriesScreen";
import { TutorialScreen } from "./components/TutorialScreen";
import { JourneyScreen } from "./components/JourneyScreen";

const MAX_LEVELS = 6;
const APPLES_PER_LEVEL = 10;

const OPPOSITE_DIRECTIONS: Record<Direction, Direction> = {
  UP: "DOWN",
  DOWN: "UP",
  LEFT: "RIGHT",
  RIGHT: "LEFT",
};

export default function App() {
  // Estado de Autenticação e Navegação
  const [currentUser, setCurrentUser] = useState<User | null>(() => authService.getCurrentUser());
  const [currentScreen, setCurrentScreen] = useState<AppScreen>(() => {
    const user = authService.getCurrentUser();
    if (!user) return "login";
    return authService.hasSeenTutorial(user.username) ? "home" : "tutorial";
  });

  const [userStats, setUserStats] = useState<UserStats>(() => {
    const user = authService.getCurrentUser();
    return user
      ? authService.getUserStats(user.username)
      : {
          highScore: 0,
          maxLevel: 1,
          gamesPlayed: 0,
          totalAcertos: 0,
          totalErros: 0,
          streakDays: 1,
          hasSeenTutorial: false,
          categoryStats: {
            saude: { acertos: 0, total: 0 },
            tecnologia: { acertos: 0, total: 0 },
            gerais: { acertos: 0, total: 0 },
          },
          achievements: [],
        };
  });

  const [selectedCategory, setSelectedCategory] = useState<CategoryFilter>("Misto");

  // Estado do Jogo e da Partida
  const [currentMatch, setCurrentMatch] = useState<Match | null>(null);
  const matchIdRef = useRef<number | null>(null);
  const [gridSize, setGridSize] = useState<number>(16);
  const [tickMs, setTickMs] = useState<number>(160);
  const [matchTimeLeft, setMatchTimeLeft] = useState<number>(120);
  const [hasAdvanced, setHasAdvanced] = useState<boolean>(false);

  const [status, setStatus] = useState<GameStatus>("START");
  const [snake, setSnake] = useState<Position[]>([
    { x: 8, y: 8 },
    { x: 7, y: 8 },
    { x: 6, y: 8 },
  ]);
  const [direction, setDirection] = useState<Direction>("RIGHT");
  const [apple, setApple] = useState<Position | null>(null);

  // Estatísticas da Partida Atual
  const [score, setScore] = useState<number>(0);
  const [level, setLevel] = useState<number>(1);
  const [applesInLevel, setApplesInLevel] = useState<number>(0);
  const [totalApples, setTotalApples] = useState<number>(0);
  const [acertos, setAcertos] = useState<number>(0);
  const [erros, setErros] = useState<number>(0);

  // Pergunta Corrente da API e Resposta
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [isQuestionAnswered, setIsQuestionAnswered] = useState<boolean>(false);
  const [lastResult, setLastResult] = useState<AnswerResult | null>(null);
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState<boolean>(false);

  // Configurações Globais
  const [isMuted, setIsMuted] = useState<boolean>(soundEffects.getMuted());
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    try {
      const saved = localStorage.getItem("fako_theme");
      if (saved === "dark" || saved === "light") return saved;
    } catch {
      // fallback
    }
    return "light";
  });

  // Referências mutáveis para loop de jogo
  const nextDirRef = useRef<Direction>("RIGHT");
  const currentDirRef = useRef<Direction>("RIGHT");
  const snakeRef = useRef<Position[]>(snake);
  const appleRef = useRef<Position | null>(apple);
  const growPendingRef = useRef<number>(0);
  const statusRef = useRef<GameStatus>(status);
  const gridSizeRef = useRef<number>(gridSize);
  const gameLoopTimerRef = useRef<number | null>(null);
  const matchCountdownTimerRef = useRef<number | null>(null);

  // Sincronizar referências
  useEffect(() => {
    snakeRef.current = snake;
  }, [snake]);

  useEffect(() => {
    appleRef.current = apple;
  }, [apple]);

  useEffect(() => {
    currentDirRef.current = direction;
  }, [direction]);

  useEffect(() => {
    statusRef.current = status;
  }, [status]);

  useEffect(() => {
    gridSizeRef.current = gridSize;
  }, [gridSize]);

  // Aplicar tema no elemento raiz
  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("fako_theme", theme);
    } catch {
      // Ignora erro
    }
  }, [theme]);

  // Sincronizar progresso com a API
  const refreshUserProgress = useCallback(async () => {
    if (!currentUser) return;
    try {
      const prog = await progressService.getMyProgress();
      setUserStats((prev) => ({
        ...prev,
        highScore: Math.max(prev.highScore, prog.total_score),
        maxLevel: prog.highest_level,
        gamesPlayed: prog.matches_played,
      }));
    } catch {
      setUserStats(authService.getUserStats(currentUser.username));
    }
  }, [currentUser]);

  useEffect(() => {
    if (currentUser) {
      refreshUserProgress();
    }
  }, [currentUser, refreshUserProgress]);

  // Posicionar maçã em célula livre
  const placeRandomApple = useCallback((currentSnake: Position[], currentGridSize: number): Position => {
    const freeCells: Position[] = [];
    for (let x = 0; x < currentGridSize; x++) {
      for (let y = 0; y < currentGridSize; y++) {
        const isOccupied = currentSnake.some((seg) => seg.x === x && seg.y === y);
        if (!isOccupied) {
          freeCells.push({ x, y });
        }
      }
    }

    if (freeCells.length === 0) {
      return { x: 0, y: 0 };
    }

    const randomIndex = Math.floor(Math.random() * freeCells.length);
    return freeCells[randomIndex];
  }, []);

  // Mudança segura de direção
  const changeDirection = useCallback((newDir: Direction) => {
    if (statusRef.current !== "PLAYING") return;
    if (OPPOSITE_DIRECTIONS[newDir] === currentDirRef.current) return;
    nextDirRef.current = newDir;
  }, []);

  // Finalizar partida na API
  const handleFinishMatch = useCallback(async (endStatus: GameStatus) => {
    if (matchCountdownTimerRef.current) {
      clearInterval(matchCountdownTimerRef.current);
      matchCountdownTimerRef.current = null;
    }
    if (gameLoopTimerRef.current) {
      clearInterval(gameLoopTimerRef.current);
      gameLoopTimerRef.current = null;
    }

    const activeMatchId = matchIdRef.current;
    matchIdRef.current = null;

    if (activeMatchId) {
      try {
        const res = await matchService.finishMatch(activeMatchId);
        setHasAdvanced(res.advanced);
      } catch (err) {
        console.error("Erro ao encerrar partida na API:", err);
      }
    }

    setStatus(endStatus);
    await refreshUserProgress();
  }, [refreshUserProgress]);

  // Passo único de movimentação da cobrinha
  const step = useCallback(async () => {
    if (statusRef.current !== "PLAYING") return;

    const currentSnake = snakeRef.current;
    const activeDir = nextDirRef.current;
    const currentGrid = gridSizeRef.current;
    setDirection(activeDir);

    let dx = 0;
    let dy = 0;
    switch (activeDir) {
      case "UP":
        dy = -1;
        break;
      case "DOWN":
        dy = 1;
        break;
      case "LEFT":
        dx = -1;
        break;
      case "RIGHT":
        dx = 1;
        break;
    }

    const head = currentSnake[0];
    const newHead: Position = {
      x: (head.x + dx + currentGrid) % currentGrid,
      y: (head.y + dy + currentGrid) % currentGrid,
    };

    // Colisão com o próprio corpo
    const hitSelf = currentSnake.some((seg) => seg.x === newHead.x && seg.y === newHead.y);
    if (hitSelf) {
      soundEffects.playGameOver();
      await handleFinishMatch("GAMEOVER");
      return;
    }

    const newSnake = [newHead, ...currentSnake];

    // Cobrinha só cresce se errou a pergunta
    if (growPendingRef.current > 0) {
      growPendingRef.current -= 1;
    } else {
      newSnake.pop();
    }

    setSnake(newSnake);

    // Checagem de maçã comida
    const currentApple = appleRef.current;
    if (currentApple && newHead.x === currentApple.x && newHead.y === currentApple.y) {
      soundEffects.playEat();
      setStatus("QUESTION");

      const activeMatchId = matchIdRef.current || 1;
      try {
        const q = await matchService.getNextQuestion(activeMatchId);
        setCurrentQuestion(q);
      } catch (err) {
        console.error("Erro ao obter próxima questão:", err);
        // Fallback caso acabe o banco de perguntas
        setCurrentQuestion({
          id: 1,
          statement: "Informações checadas e auditadas aumentam a segurança da comunidade.",
          category: "Gerais",
        });
      }

      setIsQuestionAnswered(false);
      setLastResult(null);

      const nextApplePos = placeRandomApple(newSnake, currentGrid);
      setApple(nextApplePos);
    }
  }, [placeRandomApple, handleFinishMatch]);

  // Loop de Jogo (Ticks da cobra)
  useEffect(() => {
    if (currentScreen === "game" && status === "PLAYING") {
      gameLoopTimerRef.current = window.setInterval(step, tickMs);
    } else {
      if (gameLoopTimerRef.current) {
        clearInterval(gameLoopTimerRef.current);
        gameLoopTimerRef.current = null;
      }
    }

    return () => {
      if (gameLoopTimerRef.current) {
        clearInterval(gameLoopTimerRef.current);
        gameLoopTimerRef.current = null;
      }
    };
  }, [currentScreen, status, tickMs, step]);

  // Contagem regressiva da partida (120 segundos)
  useEffect(() => {
    if (currentScreen === "game" && (status === "PLAYING" || status === "QUESTION")) {
      matchCountdownTimerRef.current = window.setInterval(() => {
        setMatchTimeLeft((prev) => {
          if (prev <= 1) {
            handleFinishMatch("TIMEOUT");
            return 0;
          }
          if (prev <= 5) {
            soundEffects.playTick();
          }
          return prev - 1;
        });
      }, 1000);
    } else {
      if (matchCountdownTimerRef.current) {
        clearInterval(matchCountdownTimerRef.current);
        matchCountdownTimerRef.current = null;
      }
    }

    return () => {
      if (matchCountdownTimerRef.current) {
        clearInterval(matchCountdownTimerRef.current);
        matchCountdownTimerRef.current = null;
      }
    };
  }, [currentScreen, status, handleFinishMatch]);

  // Iniciar Nova Partida com o Backend
  const startGame = useCallback(
    async (cat: CategoryFilter = "Misto") => {
      growPendingRef.current = 0;

      let startedMatch: Match | null = null;
      try {
        startedMatch = await matchService.startMatch(userStats.maxLevel || undefined);
      } catch (err) {
        console.error("Erro ao iniciar partida na API:", err);
      }

      const activeGrid = 16;
      const activeLvl = startedMatch?.level?.number || 1;
      const activeTick = Math.max(75, 160 - (activeLvl - 1) * 14);
      const activeDuration = startedMatch?.duration_seconds || 120;

      matchIdRef.current = startedMatch?.id || null;
      setCurrentMatch(startedMatch);
      setGridSize(activeGrid);
      setTickMs(activeTick);
      setLevel(activeLvl);
      setMatchTimeLeft(activeDuration);
      setHasAdvanced(false);

      const startX = Math.floor(activeGrid / 2);
      const startY = Math.floor(activeGrid / 2);
      const initialSnake: Position[] = [
        { x: startX, y: startY },
        { x: Math.max(0, startX - 1), y: startY },
        { x: Math.max(0, startX - 2), y: startY },
      ];

      setSnake(initialSnake);
      setDirection("RIGHT");
      nextDirRef.current = "RIGHT";

      setScore(0);
      setApplesInLevel(0);
      setTotalApples(0);
      setAcertos(0);
      setErros(0);
      setCurrentQuestion(null);
      setIsQuestionAnswered(false);
      setLastResult(null);

      const initialApple = placeRandomApple(initialSnake, activeGrid);
      setApple(initialApple);

      setStatus("PLAYING");
    },
    [userStats.maxLevel, placeRandomApple]
  );

  // Teclado
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (currentScreen !== "game") return;

      const key = e.key;
      if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " "].includes(key)) {
        e.preventDefault();
      }

      if (statusRef.current === "PLAYING") {
        if (key === "ArrowUp" || key === "w" || key === "W") changeDirection("UP");
        else if (key === "ArrowDown" || key === "s" || key === "S") changeDirection("DOWN");
        else if (key === "ArrowLeft" || key === "a" || key === "A") changeDirection("LEFT");
        else if (key === "ArrowRight" || key === "d" || key === "D") changeDirection("RIGHT");
      } else if (
        statusRef.current === "START" ||
        statusRef.current === "GAMEOVER" ||
        statusRef.current === "VICTORY" ||
        statusRef.current === "TIMEOUT"
      ) {
        if (key === "Enter" || key === " ") {
          e.preventDefault();
          startGame(selectedCategory);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentScreen, changeDirection, startGame, selectedCategory]);

  // Confirmação de Resposta via API (Confiável vs Não Confiável)
  const handleConfirmQuestion = async (answer: boolean) => {
    if (!currentQuestion || isQuestionAnswered || isSubmittingAnswer) return;

    const activeMatchId = matchIdRef.current || 1;

    setIsSubmittingAnswer(true);

    try {
      const res = await matchService.answerQuestion(
        activeMatchId,
        currentQuestion.id,
        answer
      );

      setLastResult(res);
      setScore(res.score);

      if (res.is_correct) {
        soundEffects.playCorrect();
        setAcertos((prev) => prev + 1);
      } else {
        soundEffects.playMistake();
        growPendingRef.current += 1;
        setErros((prev) => prev + 1);
      }

      setIsQuestionAnswered(true);
    } catch (err) {
      console.error("Erro ao enviar resposta à API:", err);
    } finally {
      setIsSubmittingAnswer(false);
    }
  };

  // Retomada do Jogo após Resposta
  const handleResumeGame = () => {
    const nextApplesInLevel = applesInLevel + 1;
    const nextTotalApples = totalApples + 1;
    setApplesInLevel(nextApplesInLevel);
    setTotalApples(nextTotalApples);

    setCurrentQuestion(null);
    setIsQuestionAnswered(false);
    setLastResult(null);

    setStatus("PLAYING");
  };

  // Navegação de Rotas
  const handleLoginSuccess = (user: User) => {
    setCurrentUser(user);
    refreshUserProgress();
    const stats = authService.getUserStats(user.username);
    if (!stats.hasSeenTutorial) {
      setCurrentScreen("tutorial");
    } else {
      setCurrentScreen("home");
    }
  };

  const handleLogout = () => {
    authService.logout();
    setCurrentUser(null);
    setCurrentScreen("login");
  };

  const handlePlayFromHome = (cat: CategoryFilter = "Misto") => {
    if (!currentUser) {
      setCurrentScreen("login");
      return;
    }
    const hasSeen = authService.hasSeenTutorial(currentUser.username);
    setSelectedCategory(cat);
    if (!hasSeen) {
      setCurrentScreen("tutorial");
    } else {
      setCurrentScreen("game");
      startGame(cat);
    }
  };

  const handleTutorialComplete = () => {
    if (currentUser) {
      authService.markTutorialAsSeen(currentUser.username);
    }
    setCurrentScreen("game");
    startGame(selectedCategory);
  };

  const handleTutorialSkip = () => {
    if (currentUser) {
      authService.markTutorialAsSeen(currentUser.username);
    }
    setCurrentScreen("game");
    startGame(selectedCategory);
  };

  const handleGoHome = async () => {
    if (matchIdRef.current) {
      await handleFinishMatch("GAMEOVER");
    }
    setStatus("START");
    await refreshUserProgress();
    setCurrentScreen("home");
  };

  const handleToggleMute = () => {
    const muted = soundEffects.toggleMute();
    setIsMuted(muted);
  };

  const handleToggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  const gameStats: GameStats = {
    score,
    level,
    applesInLevel,
    totalApples,
    acertos,
    erros,
    category: selectedCategory,
    advanced: hasAdvanced,
  };

  const totalAnswered = acertos + erros;
  const currentAccuracy = totalAnswered > 0 ? Math.round((acertos / totalAnswered) * 100) : 100;

  return (
    <div className={`fako-app screen-${currentScreen}`}>
      {/* 1. TELA DE LOGIN / CADASTRO */}
      {currentScreen === "login" && (
        <LoginScreen
          onLoginSuccess={handleLoginSuccess}
          theme={theme}
          onToggleTheme={handleToggleTheme}
        />
      )}

      {/* 2. TELA INICIAL (DASHBOARD FIGMA) */}
      {currentScreen === "home" && currentUser && (
        <HomeScreen
          user={currentUser}
          stats={userStats}
          onPlay={() => handlePlayFromHome("Misto")}
          onSelectCategory={(cat) => handlePlayFromHome(cat)}
          onCategories={() => setCurrentScreen("categories")}
          onTutorial={() => setCurrentScreen("tutorial")}
          onJourney={() => setCurrentScreen("journey")}
          onLogout={handleLogout}
          isMuted={isMuted}
          onToggleMute={handleToggleMute}
          theme={theme}
          onToggleTheme={handleToggleTheme}
        />
      )}

      {/* 3. TELA DE CATEGORIAS */}
      {currentScreen === "categories" && (
        <CategoriesScreen
          onSelectCategory={(cat) => handlePlayFromHome(cat)}
          onBack={() => setCurrentScreen("home")}
        />
      )}

      {/* 4. TELA DE TUTORIAL */}
      {currentScreen === "tutorial" && (
        <TutorialScreen
          onComplete={handleTutorialComplete}
          onSkip={handleTutorialSkip}
        />
      )}

      {/* 5. TELA MINHA JORNADA */}
      {currentScreen === "journey" && currentUser && (
        <JourneyScreen
          user={currentUser}
          stats={userStats}
          onBack={() => setCurrentScreen("home")}
          onPlay={() => handlePlayFromHome("Misto")}
        />
      )}

      {/* 6. TELA DO JOGO (SNAKE INTEGRADO AO BACKEND) */}
      {currentScreen === "game" && (
        <main className="game-screen-wrapper">
          {/* Header Mobile / Topo com Cronômetro de 120s da Partida */}
          <div className="game-top-bar-mobile">
            <Header
              score={score}
              level={level}
              applesInLevel={applesInLevel}
              maxApplesPerLevel={APPLES_PER_LEVEL}
              maxLevels={MAX_LEVELS}
              matchTimeLeft={matchTimeLeft}
              isMuted={isMuted}
              onToggleMute={handleToggleMute}
              theme={theme}
              onToggleTheme={handleToggleTheme}
              onGoHome={handleGoHome}
              username={currentUser?.username}
            />
          </div>

          <div className="game-expanded-layout">
            {/* Coluna Esquerda: Telemetria e Vidas */}
            <aside className="game-side-panel left-panel">
              <div className="side-card main-stats-card">
                <span className="side-card-badge">🍏 Partida FAKO</span>
                <div className="side-stat-row">
                  <span className="side-stat-label">Pontos</span>
                  <span className="side-stat-val text-accent">{score}</span>
                </div>
                <div className="side-stat-row">
                  <span className="side-stat-label">Tempo Restante</span>
                  <span className={`side-stat-val ${matchTimeLeft <= 20 ? "text-danger" : ""}`}>
                    {matchTimeLeft}s
                  </span>
                </div>
                <div className="side-stat-row">
                  <span className="side-stat-label">Nível</span>
                  <span className="side-stat-val">
                    {level} <small>/ {MAX_LEVELS}</small>
                  </span>
                </div>
                <div className="side-progress-box">
                  <div className="side-progress-header">
                    <span>Meta de Pontos</span>
                    <span>
                      {score} / {currentMatch?.level?.min_score_to_advance ?? 30} pts
                    </span>
                  </div>
                  <div className="side-progress-track">
                    <div
                      className="side-progress-fill"
                      style={{
                        width: `${Math.min(
                          100,
                          (score / (currentMatch?.level?.min_score_to_advance || 30)) * 100
                        )}%`,
                      }}
                    />
                  </div>
                </div>
              </div>

              <div className="side-card snake-status-card">
                <h4 className="side-card-title">🐍 Status da Cobra</h4>
                <div className="side-metric-item">
                  <span className="metric-name">Grade do Tabuleiro</span>
                  <span className="metric-val">{gridSize}×{gridSize}</span>
                </div>
                <div className="side-metric-item">
                  <span className="metric-name">Comprimento</span>
                  <span className="metric-val">{snake.length} blocos</span>
                </div>
                <div className="side-metric-item">
                  <span className="metric-name">Crescimento no erro</span>
                  <span className="metric-val text-danger">+{erros}</span>
                </div>
              </div>
            </aside>

            {/* Coluna Central: O Tabuleiro */}
            <section className="game-center-board">
              <div className="board-interactive-area">
                <GameBoard
                  gridSize={gridSize}
                  snake={snake}
                  direction={direction}
                  apple={apple}
                  onSwipe={changeDirection}
                />

                {/* Modal da Pergunta Confiável / Não Confiável */}
                {status === "QUESTION" && currentQuestion && (
                  <QuestionModal
                    question={currentQuestion}
                    isAnswered={isQuestionAnswered}
                    result={lastResult}
                    onConfirm={handleConfirmQuestion}
                    onResume={handleResumeGame}
                    isSubmitting={isSubmittingAnswer}
                  />
                )}

                {/* Telas de Início, Fim de Jogo, Tempo Esgotado e Vitória */}
                <OverlayScreen
                  status={status}
                  stats={gameStats}
                  onStart={() => startGame(selectedCategory)}
                  onRestart={() => startGame(selectedCategory)}
                  onGoHome={handleGoHome}
                />
              </div>

              {/* Controles Virtuais D-pad */}
              <DpadControls
                onDirectionChange={changeDirection}
                disabled={status !== "PLAYING"}
              />
            </section>

            {/* Coluna Direita: Análise Crítica e Controles Rápidos */}
            <aside className="game-side-panel right-panel">
              <div className="side-card session-category-card">
                <span className="side-card-badge">Área Temática</span>
                <h4 className="category-active-title">
                  {selectedCategory === "Misto" ? "🎲 Modo Desafio Misto" : selectedCategory}
                </h4>
                <p className="category-active-desc">
                  Afirmações reais auditadas contra desinformação com referências científicas e institucionais.
                </p>
              </div>

              <div className="side-card accuracy-card">
                <h4 className="side-card-title">🎯 Precisão da Rodada</h4>
                <div className="accuracy-big-number">{currentAccuracy}%</div>
                <div className="side-counts-row">
                  <span className="count-hit">✅ {acertos} acertos</span>
                  <span className="count-miss">❌ {erros} erros</span>
                </div>
              </div>

              <div className="side-card quick-nav-card">
                <button
                  type="button"
                  className="secondary-button side-nav-btn"
                  onClick={handleGoHome}
                >
                  🏠 Voltar ao Hub
                </button>
                <button
                  type="button"
                  className="secondary-button side-nav-btn"
                  onClick={() => setCurrentScreen("tutorial")}
                >
                  📖 Ver Regras
                </button>
              </div>
            </aside>
          </div>
        </main>
      )}
    </div>
  );
}
