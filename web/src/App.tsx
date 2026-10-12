import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AnswerResult,
  AnsweredQuestion,
  AppScreen,
  Direction,
  GameStatus,
  Level,
  Match,
  MatchEndReason,
  MatchRecord,
  Position,
  Question,
  User,
  UserProgress,
  UserStats,
} from "./types";
import { soundEffects } from "./services/audioService";
import { authService } from "./services/authService";
import { HttpError } from "./services/httpClient";
import { matchService } from "./services/matchService";
import { progressService } from "./services/progressService";
import { LOCAL_LEVELS, levelService } from "./services/levelService";
import { clampReliability } from "./utils/formatters";
import { AppHeader, HeaderTab } from "./components/AppHeader";
import { GameScreen } from "./components/GameScreen";
import { HomeScreen } from "./components/HomeScreen";
import { JourneyScreen } from "./components/JourneyScreen";
import { LoginScreen } from "./components/LoginScreen";
import { ExitMatchDialog, HowToPlayDialog } from "./components/MatchDialogs";
import { MatchHud } from "./components/MatchHud";
import { MatchSummary } from "./components/MatchSummary";
import { QuestionPopup, ResultPopup } from "./components/QuestionModal";
import { TutorialScreen } from "./components/TutorialScreen";

// Regras da partida exibidas ao jogador (a pontuação oficial vem da API).
const MATCH_SECONDS = 120;
const QUESTION_SECONDS = 45;
const COUNTDOWN_SECONDS = 3;
const POINTS_PER_CORRECT = 10;
const GRID_SIZE = 16;
const INITIAL_RELIABILITY = 50;

const OPPOSITE_DIRECTIONS: Record<Direction, Direction> = {
  UP: "DOWN",
  DOWN: "UP",
  LEFT: "RIGHT",
  RIGHT: "LEFT",
};

const KEY_DIRECTIONS: Record<string, Direction> = {
  ArrowUp: "UP",
  ArrowDown: "DOWN",
  ArrowLeft: "LEFT",
  ArrowRight: "RIGHT",
  w: "UP",
  s: "DOWN",
  a: "LEFT",
  d: "RIGHT",
};

const tickForLevel = (level: number) => Math.max(75, 160 - (level - 1) * 14);

const initialSnake = (): Position[] => {
  const middle = Math.floor(GRID_SIZE / 2);
  return [
    { x: middle, y: middle },
    { x: middle - 1, y: middle },
    { x: middle - 2, y: middle },
  ];
};

function placeRandomApple(snake: Position[]): Position {
  const freeCells: Position[] = [];
  for (let x = 0; x < GRID_SIZE; x++) {
    for (let y = 0; y < GRID_SIZE; y++) {
      if (!snake.some((segment) => segment.x === x && segment.y === y)) freeCells.push({ x, y });
    }
  }
  return freeCells.length > 0 ? freeCells[Math.floor(Math.random() * freeCells.length)] : { x: 0, y: 0 };
}

function readSavedTheme(): "light" | "dark" {
  try {
    const saved = localStorage.getItem("fako_theme");
    if (saved === "dark" || saved === "light") return saved;
  } catch {
    // Sem armazenamento local, segue no tema claro
  }
  return "light";
}

interface MatchEnding {
  reason: MatchEndReason;
  advanced: boolean;
  secondsPlayed: number;
  snakeLength: number;
}

export default function App() {
  // Sessão, navegação e preferências
  const [currentUser, setCurrentUser] = useState<User | null>(() => authService.getCurrentUser());
  const [currentScreen, setCurrentScreen] = useState<AppScreen>(() => {
    const user = authService.getCurrentUser();
    if (!user) return "login";
    return authService.hasSeenTutorial(user.username) ? "home" : "tutorial";
  });
  const [loginNotice, setLoginNotice] = useState<string | null>(null);
  const [theme, setTheme] = useState<"light" | "dark">(readSavedTheme);

  // Registrado antes dos efeitos que chamam a API, para pegar o 401 do token vencido.
  useEffect(
    () =>
      authService.onSessionExpired(() => {
        setCurrentUser(null);
        setCurrentScreen("login");
        setLoginNotice("Sua sessão expirou. Entre novamente para salvar o seu progresso.");
      }),
    []
  );
  const [isMuted, setIsMuted] = useState<boolean>(soundEffects.getMuted());

  // Progresso: estatísticas locais (histórico, conquistas) e progresso oficial da API
  const [userStats, setUserStats] = useState<UserStats>(() => {
    const user = authService.getCurrentUser();
    return authService.getUserStats(user?.username ?? "");
  });
  const [progress, setProgress] = useState<UserProgress>({
    current_level: 1,
    highest_level: 1,
    total_score: 0,
    matches_played: 0,
  });
  const [levels, setLevels] = useState<Level[]>(LOCAL_LEVELS);

  // Partida
  const [currentMatch, setCurrentMatch] = useState<Match | null>(null);
  const [status, setStatus] = useState<GameStatus>("COUNTDOWN");
  const [level, setLevel] = useState(1);
  const [tickMs, setTickMs] = useState(tickForLevel(1));
  const [matchDuration, setMatchDuration] = useState(MATCH_SECONDS);
  const [timeLeft, setTimeLeft] = useState(MATCH_SECONDS);
  const [countdownLeft, setCountdownLeft] = useState(COUNTDOWN_SECONDS);
  const [snake, setSnake] = useState<Position[]>(initialSnake);
  const [direction, setDirection] = useState<Direction>("RIGHT");
  const [apple, setApple] = useState<Position | null>(null);
  const [score, setScore] = useState(0);
  const [answers, setAnswers] = useState<AnsweredQuestion[]>([]);
  const [ending, setEnding] = useState<MatchEnding | null>(null);

  // Pergunta e resultado
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [reliability, setReliability] = useState(INITIAL_RELIABILITY);
  const [questionSecondsLeft, setQuestionSecondsLeft] = useState(QUESTION_SECONDS);
  const [lastResult, setLastResult] = useState<AnswerResult | null>(null);
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false);

  // Janelas sobre a partida (pausam o jogo enquanto abertas)
  const [dialog, setDialog] = useState<"exit" | "howto" | null>(null);

  // Referências lidas pelo loop do jogo sem recriar os intervalos
  const statusRef = useRef<GameStatus>(status);
  const snakeRef = useRef<Position[]>(snake);
  const appleRef = useRef<Position | null>(apple);
  const nextDirectionRef = useRef<Direction>("RIGHT");
  const currentDirectionRef = useRef<Direction>("RIGHT");
  const growPendingRef = useRef(0);
  const matchIdRef = useRef<number | null>(null);
  const statusBeforeDialogRef = useRef<GameStatus>("PLAYING");
  const finishingRef = useRef(false);
  const remainingMsRef = useRef(MATCH_SECONDS * 1000);

  const changeStatus = useCallback((next: GameStatus) => {
    statusRef.current = next;
    setStatus(next);
  }, []);

  useEffect(() => {
    snakeRef.current = snake;
  }, [snake]);

  useEffect(() => {
    appleRef.current = apple;
  }, [apple]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("fako_theme", theme);
    } catch {
      // Preferência fica só nesta sessão
    }
  }, [theme]);

  const refreshProgress = useCallback(async () => {
    if (!currentUser) return;
    setProgress(await progressService.getMyProgress());
  }, [currentUser]);

  useEffect(() => {
    if (!currentUser) return;
    setUserStats(authService.getUserStats(currentUser.username));
    refreshProgress();
    levelService.listLevels().then((list) => {
      if (list.length > 0) setLevels([...list].sort((a, b) => a.number - b.number));
    });
  }, [currentUser, refreshProgress]);

  const maxLevels = levels.length;
  const levelConfig = (number: number) => levels.find((item) => item.number === number);
  const minScoreToAdvance = currentMatch?.level.min_score_to_advance ?? levelConfig(level)?.min_score_to_advance ?? 30;
  const blocksFromErrors = answers.filter((answer) => !answer.isCorrect).length;
  const acertos = answers.length - blocksFromErrors;

  // Melhor partida no nível atual: base do "faltam X pts".
  const bestScoreInCurrentLevel = useMemo(
    () =>
      userStats.history
        .filter((match) => match.level === progress.current_level)
        .reduce((best, match) => Math.max(best, match.score), 0),
    [userStats.history, progress.current_level]
  );
  const missingPoints = Math.max(
    0,
    (levelConfig(progress.current_level)?.min_score_to_advance ?? 30) - bestScoreInCurrentLevel
  );

  // ---------------------------------------------------------------- partida

  // Valores atuais para o encerramento, sem recriar o loop da cobra a cada segundo.
  const latestRef = useRef({ level, matchDuration, timeLeft, score, answers, currentUser });
  latestRef.current = { level, matchDuration, timeLeft, score, answers, currentUser };

  const finishMatch = useCallback(
    async (reason: MatchEndReason) => {
      if (finishingRef.current) return;
      finishingRef.current = true;
      changeStatus("FINISHED");
      setDialog(null);

      const { level, matchDuration, timeLeft, score, answers, currentUser } = latestRef.current;
      const erros = answers.filter((answer) => !answer.isCorrect).length;
      const activeMatchId = matchIdRef.current;
      matchIdRef.current = null;
      let advanced = false;
      let unlockedLevel = level;
      if (activeMatchId) {
        try {
          const result = await matchService.finishMatch(activeMatchId);
          advanced = result.advanced;
          unlockedLevel = result.current_level;
        } catch (error) {
          console.error("Erro ao encerrar a partida na API:", error);
        }
      }

      const secondsPlayed = matchDuration - timeLeft;
      const snakeLength = snakeRef.current.length;
      setEnding({ reason, advanced, secondsPlayed, snakeLength });

      if (currentUser) {
        const record: MatchRecord = {
          finishedAt: Date.now(),
          level,
          score,
          acertos: answers.length - erros,
          erros,
          snakeLength,
          secondsPlayed,
          endReason: reason,
          answers,
        };
        setUserStats(authService.recordMatchFinished(currentUser.username, record, unlockedLevel));
      }
      await refreshProgress();
    },
    [changeStatus, refreshProgress]
  );

  const startGame = useCallback(
    async (levelNumber?: number) => {
      finishingRef.current = false;
      growPendingRef.current = 0;
      setDialog(null);
      setEnding(null);

      let match: Match | null = null;
      try {
        match = await matchService.startMatch(levelNumber ?? progress.current_level);
      } catch (error) {
        console.error("Erro ao iniciar a partida na API:", error);
      }
      if (!authService.getCurrentUser()) return; // a sessão expirou durante o pedido

      const matchLevel = match?.level.number ?? levelNumber ?? 1;
      const duration = match?.duration_seconds ?? MATCH_SECONDS;
      const startSnake = initialSnake();

      matchIdRef.current = match?.id ?? null;
      setCurrentMatch(match);
      setLevel(matchLevel);
      setTickMs(tickForLevel(matchLevel));
      setMatchDuration(duration);
      setTimeLeft(duration);
      remainingMsRef.current = duration * 1000;
      setSnake(startSnake);
      snakeRef.current = startSnake;
      setDirection("RIGHT");
      nextDirectionRef.current = "RIGHT";
      currentDirectionRef.current = "RIGHT";
      const firstApple = placeRandomApple(startSnake);
      setApple(firstApple);
      appleRef.current = firstApple;
      setScore(0);
      setAnswers([]);
      setCurrentQuestion(null);
      setLastResult(null);
      setCountdownLeft(COUNTDOWN_SECONDS);
      setCurrentScreen("game");
      changeStatus("COUNTDOWN");
    },
    [progress.current_level, changeStatus]
  );

  const resumeWithCountdown = useCallback(() => {
    setCountdownLeft(COUNTDOWN_SECONDS);
    changeStatus("COUNTDOWN");
  }, [changeStatus]);

  const openQuestion = useCallback(async () => {
    changeStatus("QUESTION");
    setCurrentQuestion(null);
    setLastResult(null);
    setReliability(INITIAL_RELIABILITY);
    setQuestionSecondsLeft(QUESTION_SECONDS);
    try {
      setCurrentQuestion(await matchService.getNextQuestion(matchIdRef.current ?? 0));
    } catch (error) {
      if (error instanceof HttpError && error.status === 404) {
        finishMatch("NO_QUESTIONS");
        return;
      }
      console.error("Erro ao buscar a próxima afirmação:", error);
      resumeWithCountdown();
    }
  }, [changeStatus, finishMatch, resumeWithCountdown]);

  // Um passo da cobrinha
  const step = useCallback(() => {
    if (statusRef.current !== "PLAYING") return;

    const currentSnake = snakeRef.current;
    const activeDirection = nextDirectionRef.current;
    currentDirectionRef.current = activeDirection;
    setDirection(activeDirection);

    const delta = { UP: [0, -1], DOWN: [0, 1], LEFT: [-1, 0], RIGHT: [1, 0] }[activeDirection];
    const head = currentSnake[0];
    const newHead: Position = {
      x: (head.x + delta[0] + GRID_SIZE) % GRID_SIZE,
      y: (head.y + delta[1] + GRID_SIZE) % GRID_SIZE,
    };

    if (currentSnake.some((segment) => segment.x === newHead.x && segment.y === newHead.y)) {
      soundEffects.playGameOver();
      finishMatch("GAMEOVER");
      return;
    }

    const newSnake = [newHead, ...currentSnake];
    // A cobrinha só cresce depois de um erro
    if (growPendingRef.current > 0) {
      growPendingRef.current -= 1;
    } else {
      newSnake.pop();
    }
    snakeRef.current = newSnake;
    setSnake(newSnake);

    const currentApple = appleRef.current;
    if (currentApple && newHead.x === currentApple.x && newHead.y === currentApple.y) {
      soundEffects.playEat();
      const nextApple = placeRandomApple(newSnake);
      appleRef.current = nextApple;
      setApple(nextApple);
      openQuestion();
    }
  }, [finishMatch, openQuestion]);

  const changeDirection = useCallback((next: Direction) => {
    if (statusRef.current !== "PLAYING") return;
    if (OPPOSITE_DIRECTIONS[next] === currentDirectionRef.current) return;
    nextDirectionRef.current = next;
  }, []);

  // Loop da cobrinha
  useEffect(() => {
    if (currentScreen !== "game" || status !== "PLAYING") return;
    const timer = window.setInterval(step, tickMs);
    return () => window.clearInterval(timer);
  }, [currentScreen, status, tickMs, step]);

  // Cronômetro da partida: só corre com a cobra andando. Acumula o tempo real em ms
  // para que trechos curtos entre uma pergunta e outra também descontem.
  useEffect(() => {
    if (currentScreen !== "game" || status !== "PLAYING") return;
    let last = performance.now();
    const consume = () => {
      const now = performance.now();
      remainingMsRef.current = Math.max(0, remainingMsRef.current - (now - last));
      last = now;
      setTimeLeft(Math.ceil(remainingMsRef.current / 1000));
    };
    const timer = window.setInterval(consume, 200);
    return () => {
      window.clearInterval(timer);
      consume();
    };
  }, [currentScreen, status]);

  useEffect(() => {
    if (status !== "PLAYING") return;
    if (timeLeft <= 0) finishMatch("TIMEOUT");
    else if (timeLeft <= 5) soundEffects.playTick();
  }, [timeLeft, status, finishMatch]);

  // Contagem de 3 s antes de a cobra andar
  useEffect(() => {
    if (currentScreen !== "game" || status !== "COUNTDOWN") return;
    if (countdownLeft <= 0) {
      changeStatus("PLAYING");
      return;
    }
    const timer = window.setTimeout(() => setCountdownLeft((previous) => previous - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [currentScreen, status, countdownLeft, changeStatus]);

  // ---------------------------------------------------------------- pergunta

  const confirmAnswer = useCallback(async () => {
    if (!currentQuestion || isSubmittingAnswer || statusRef.current !== "QUESTION") return;
    setIsSubmittingAnswer(true);
    const question = currentQuestion;
    const value = clampReliability(reliability);
    try {
      const result = await matchService.answerQuestion(matchIdRef.current ?? 0, question.id, value);
      setLastResult(result);
      // A API devolve o placar oficial; se ela cair no meio da partida, a pergunta local
      // ainda soma os pontos do acerto.
      setScore(result.score);
      setAnswers((previous) => [
        ...previous,
        {
          statement: question.statement,
          reliability: result.reliability,
          reference: result.reliability_reference,
          isCorrect: result.is_correct,
        },
      ]);
      if (result.is_correct) {
        soundEffects.playCorrect();
      } else {
        soundEffects.playMistake();
        growPendingRef.current += 1;
      }
      changeStatus("FEEDBACK");
    } catch (error) {
      // Sem a correção da API não há como avaliar: a pergunta sai sem pontuar nem penalizar.
      console.error("Erro ao enviar a resposta:", error);
      setCurrentQuestion(null);
      resumeWithCountdown();
    } finally {
      setIsSubmittingAnswer(false);
    }
  }, [currentQuestion, isSubmittingAnswer, reliability, changeStatus, resumeWithCountdown]);

  // 45 s por pergunta; no fim do tempo vale o valor marcado na barra
  useEffect(() => {
    if (status !== "QUESTION" || !currentQuestion || isSubmittingAnswer) return;
    if (questionSecondsLeft <= 0) {
      confirmAnswer();
      return;
    }
    const timer = window.setTimeout(() => setQuestionSecondsLeft((previous) => previous - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [status, currentQuestion, isSubmittingAnswer, questionSecondsLeft, confirmAnswer]);

  const continueAfterFeedback = useCallback(() => {
    setCurrentQuestion(null);
    setLastResult(null);
    resumeWithCountdown();
  }, [resumeWithCountdown]);

  // ---------------------------------------------------------------- janelas e pausa

  const openDialog = useCallback(
    (which: "exit" | "howto") => {
      if (statusRef.current === "FINISHED") return;
      // Durante a contagem a janela volta direto para a cobra andando
      statusBeforeDialogRef.current = statusRef.current === "COUNTDOWN" ? "PLAYING" : statusRef.current;
      setDialog(which);
      changeStatus("PAUSED");
    },
    [changeStatus]
  );

  const closeDialog = useCallback(() => {
    setDialog(null);
    const previous = statusBeforeDialogRef.current;
    if (previous === "PLAYING") resumeWithCountdown();
    else changeStatus(previous);
  }, [resumeWithCountdown, changeStatus]);

  const togglePause = useCallback(() => {
    if (statusRef.current === "PLAYING") changeStatus("PAUSED");
    else if (statusRef.current === "PAUSED" && !dialog) resumeWithCountdown();
  }, [changeStatus, resumeWithCountdown, dialog]);

  const exitAndSave = useCallback(async () => {
    await finishMatch("EXIT");
    setCurrentScreen("home");
  }, [finishMatch]);

  // Teclado da partida
  useEffect(() => {
    if (currentScreen !== "game") return;
    const handleKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const onButton = target?.tagName === "BUTTON";
      const onSlider = target instanceof HTMLInputElement && target.type === "range";
      const current = statusRef.current;
      const keyDirection = KEY_DIRECTIONS[event.key] ?? KEY_DIRECTIONS[event.key.toLowerCase()];

      if (event.key === "Escape") {
        event.preventDefault();
        if (dialog) closeDialog();
        else togglePause();
        return;
      }

      if (current === "PLAYING") {
        if (keyDirection) {
          event.preventDefault();
          changeDirection(keyDirection);
        } else if (event.key === " ") {
          event.preventDefault();
        }
        return;
      }

      if (current === "QUESTION") {
        // Com o foco na barra, as setas já mexem no input range
        if (!onSlider && (event.key === "ArrowLeft" || event.key === "ArrowRight")) {
          event.preventDefault();
          setReliability((previous) => clampReliability(previous + (event.key === "ArrowRight" ? 5 : -5)));
        } else if (event.key === "Enter" && !onButton) {
          event.preventDefault();
          confirmAnswer();
        }
        return;
      }

      if (event.key === "Enter" && !onButton) {
        if (current === "FEEDBACK") {
          event.preventDefault();
          continueAfterFeedback();
        } else if (current === "FINISHED") {
          event.preventDefault();
          startGame(level);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentScreen, dialog, closeDialog, togglePause, changeDirection, confirmAnswer, continueAfterFeedback, startGame, level]);

  // ---------------------------------------------------------------- navegação

  const handleLoginSuccess = (user: User) => {
    setLoginNotice(null);
    setCurrentUser(user);
    setCurrentScreen(authService.hasSeenTutorial(user.username) ? "home" : "tutorial");
  };

  const handleLogout = () => {
    authService.logout();
    setCurrentUser(null);
    setCurrentScreen("login");
  };

  const markTutorialSeen = () => {
    if (currentUser) authService.markTutorialAsSeen(currentUser.username);
  };

  const handleNavigate = (tab: HeaderTab) => {
    setCurrentScreen(tab === "home" ? "home" : tab === "journey" ? "journey" : "tutorial");
  };

  const handleGoHome = () => {
    setCurrentScreen("home");
    changeStatus("COUNTDOWN");
  };

  const handleToggleMute = () => setIsMuted(soundEffects.toggleMute());
  const handleToggleTheme = () => setTheme((previous) => (previous === "dark" ? "light" : "dark"));

  // ---------------------------------------------------------------- telas

  if (currentScreen === "login" || !currentUser) {
    return (
      <div className="fako-app screen-login">
        <LoginScreen
          onLoginSuccess={handleLoginSuccess}
          theme={theme}
          onToggleTheme={handleToggleTheme}
          notice={loginNotice}
        />
      </div>
    );
  }

  if (currentScreen === "tutorial") {
    return (
      <div className="fako-app screen-tutorial">
        <TutorialScreen
          questionSeconds={QUESTION_SECONDS}
          pointsPerCorrect={POINTS_PER_CORRECT}
          onComplete={() => {
            markTutorialSeen();
            startGame();
          }}
          onSkip={() => {
            markTutorialSeen();
            setCurrentScreen("home");
          }}
        />
      </div>
    );
  }

  if (currentScreen === "game") {
    const isLastLevel = level >= maxLevels;
    return (
      <div className="fako-app screen-game">
        <div className="page-shell page-shell--game">
          <MatchHud
            level={level}
            boardSize={GRID_SIZE}
            status={status}
            timeLeft={timeLeft}
            duration={matchDuration}
            score={score}
            onExit={() => openDialog("exit")}
          />

          {status === "FINISHED" && ending ? (
            <MatchSummary
              username={currentUser.username}
              endReason={ending.reason}
              score={score}
              level={level}
              maxLevel={maxLevels}
              minScoreToAdvance={minScoreToAdvance}
              advanced={ending.advanced}
              answers={answers}
              snakeLength={ending.snakeLength}
              secondsPlayed={ending.secondsPlayed}
              pointsPerCorrect={POINTS_PER_CORRECT}
              onPlayAgain={() => startGame(ending.advanced ? undefined : level)}
              onGoHome={handleGoHome}
              onOpenJourney={() => setCurrentScreen("journey")}
            />
          ) : (
            <GameScreen
              status={status}
              level={level}
              score={score}
              minScoreToAdvance={minScoreToAdvance}
              isLastLevel={isLastLevel}
              gridSize={GRID_SIZE}
              snake={snake}
              direction={direction}
              apple={apple}
              blocksFromErrors={blocksFromErrors}
              countdownLeft={countdownLeft}
              countdownTotal={COUNTDOWN_SECONDS}
              onDirection={changeDirection}
              onTogglePause={togglePause}
              onHowToPlay={() => openDialog("howto")}
            />
          )}
        </div>

        {status === "QUESTION" && (
          <QuestionPopup
            question={currentQuestion}
            reliability={reliability}
            secondsLeft={questionSecondsLeft}
            isSubmitting={isSubmittingAnswer}
            onChangeReliability={(value) => setReliability(clampReliability(value))}
            onConfirm={confirmAnswer}
          />
        )}

        {status === "FEEDBACK" && lastResult && currentQuestion && (
          <ResultPopup
            statement={currentQuestion.statement}
            result={lastResult}
            pointsPerCorrect={POINTS_PER_CORRECT}
            onContinue={continueAfterFeedback}
          />
        )}

        {dialog === "exit" && (
          <ExitMatchDialog
            score={score}
            acertos={acertos}
            answered={answers.length}
            timeLeft={timeLeft}
            onContinue={closeDialog}
            onExit={exitAndSave}
          />
        )}

        {dialog === "howto" && (
          <HowToPlayDialog
            questionSeconds={QUESTION_SECONDS}
            pointsPerCorrect={POINTS_PER_CORRECT}
            onClose={closeDialog}
          />
        )}
      </div>
    );
  }

  return (
    <div className={`fako-app screen-${currentScreen}`}>
      <div className="page-shell">
        <AppHeader
          active={currentScreen === "journey" ? "journey" : "home"}
          username={currentUser.username}
          level={progress.current_level}
          totalScore={progress.total_score}
          isMuted={isMuted}
          theme={theme}
          onNavigate={handleNavigate}
          onToggleTheme={handleToggleTheme}
          onToggleMute={handleToggleMute}
          onLogout={handleLogout}
        />

        {currentScreen === "journey" ? (
          <JourneyScreen
            levels={levels}
            currentLevel={progress.current_level}
            highestLevel={progress.highest_level}
            totalScore={progress.total_score}
            matchesPlayed={progress.matches_played}
            bestScoreInLevel={bestScoreInCurrentLevel}
            stats={userStats}
            onPlayLevel={(number) => startGame(number)}
          />
        ) : (
          <HomeScreen
            username={currentUser.username}
            currentLevel={progress.current_level}
            maxLevels={maxLevels}
            missingPoints={missingPoints}
            matchSeconds={MATCH_SECONDS}
            stats={userStats}
            matchesPlayed={progress.matches_played}
            onPlay={() => startGame()}
            onTutorial={() => setCurrentScreen("tutorial")}
          />
        )}
      </div>
    </div>
  );
}
