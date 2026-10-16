import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
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
import { HttpError, isGuestSession } from "./services/httpClient";
import { matchService } from "./services/matchService";
import { progressService } from "./services/progressService";
import { LOCAL_LEVELS, levelService } from "./services/levelService";
import {
  hitsBody,
  initialSnake,
  nextHead,
  randomFreeCell,
  sameCell,
} from "./utils/board";
import { clampReliability } from "./utils/formatters";
import { AppHeader, HeaderTab } from "./components/AppHeader";
import { AppNotice } from "./components/AppNotice";
import { GameScreen } from "./components/GameScreen";
import { HomeScreen } from "./components/HomeScreen";
import { JourneyScreen } from "./components/JourneyScreen";
import { LoginScreen } from "./components/LoginScreen";
import { ExitMatchDialog, HowToPlayDialog } from "./components/MatchDialogs";
import { MatchHud } from "./components/MatchHud";
import { MatchSummary } from "./components/MatchSummary";
import { QuestionPopup, ResultPopup } from "./components/QuestionModal";
import { TutorialScreen } from "./components/TutorialScreen";

// Regras da partida exibidas ao jogador (a pontuação oficial vem da API). O que muda por
// nível (tabuleiro, velocidade, tempos, tolerância...) vem do nível da partida.
const COUNTDOWN_SECONDS = 3;
const POINTS_PER_CORRECT = 10;
const INITIAL_RELIABILITY = 50;
// Blocos que a cobra cresce ao comer a maçã podre.
const ROTTEN_APPLE_GROWTH = 2;
// A maçã com prazo pisca nos últimos instantes antes de mudar de lugar.
const APPLE_FADING_MS = 2000;
const FIRST_LEVEL = LOCAL_LEVELS[0];

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

function readSavedTheme(): "light" | "dark" {
  try {
    const saved = localStorage.getItem("fako_theme");
    if (saved === "dark" || saved === "light") return saved;
  } catch {
    // Sem armazenamento local, segue no tema claro
  }
  return "light";
}

const DEFAULT_PROGRESS: UserProgress = {
  current_level: 1,
  highest_level: 1,
  total_score: 0,
  matches_played: 0,
};

function errorText(error: unknown, fallback: string): string {
  return error instanceof HttpError && error.message ? error.message : fallback;
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
  // Aviso sobre a partida (não começou, não foi salva...), mostrado acima da tela
  const [appNotice, setAppNotice] = useState<string | null>(null);
  const [theme, setTheme] = useState<"light" | "dark">(readSavedTheme);

  const [isMuted, setIsMuted] = useState<boolean>(soundEffects.getMuted());

  // Progresso: estatísticas locais (histórico, conquistas) e progresso oficial da API
  const [userStats, setUserStats] = useState<UserStats>(() => {
    const user = authService.getCurrentUser();
    return authService.getUserStats(user?.username ?? "");
  });
  const [progress, setProgress] = useState<UserProgress>(DEFAULT_PROGRESS);
  const [levels, setLevels] = useState<Level[]>(LOCAL_LEVELS);

  // Registrado antes dos efeitos que chamam a API, para pegar o 401 do token vencido.
  useEffect(
    () =>
      authService.onSessionExpired(() => {
        setCurrentUser(null);
        setProgress(DEFAULT_PROGRESS);
        setCurrentScreen("login");
        setLoginNotice("Sua sessão expirou. Entre novamente para salvar o seu progresso.");
      }),
    []
  );

  // Partida
  const [currentMatch, setCurrentMatch] = useState<Match | null>(null);
  const [status, setStatus] = useState<GameStatus>("COUNTDOWN");
  const [level, setLevel] = useState(1);
  // Regras do nível da partida em andamento
  const [rules, setRules] = useState<Level>(FIRST_LEVEL);
  const [matchDuration, setMatchDuration] = useState(FIRST_LEVEL.match_seconds);
  const [timeLeft, setTimeLeft] = useState(FIRST_LEVEL.match_seconds);
  const [countdownLeft, setCountdownLeft] = useState(COUNTDOWN_SECONDS);
  const [snake, setSnake] = useState<Position[]>(() => initialSnake(FIRST_LEVEL.board_size));
  const [direction, setDirection] = useState<Direction>("RIGHT");
  const [apple, setApple] = useState<Position | null>(null);
  const [rottenApples, setRottenApples] = useState<Position[]>([]);
  const [isAppleFading, setIsAppleFading] = useState(false);
  const [score, setScore] = useState(0);
  const [answers, setAnswers] = useState<AnsweredQuestion[]>([]);
  const [ending, setEnding] = useState<MatchEnding | null>(null);

  // Pergunta e resultado
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [reliability, setReliability] = useState(INITIAL_RELIABILITY);
  const [questionSecondsLeft, setQuestionSecondsLeft] = useState(FIRST_LEVEL.question_seconds);
  const [lastResult, setLastResult] = useState<AnswerResult | null>(null);
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false);

  // Janelas sobre a partida (pausam o jogo enquanto abertas)
  const [dialog, setDialog] = useState<"exit" | "howto" | null>(null);

  // Referências lidas pelo loop do jogo sem recriar os intervalos
  const statusRef = useRef<GameStatus>(status);
  const snakeRef = useRef<Position[]>(snake);
  const appleRef = useRef<Position | null>(apple);
  const rottenApplesRef = useRef<Position[]>([]);
  const rulesRef = useRef<Level>(FIRST_LEVEL);
  // Tempo de cobra andando desde que a maçã apareceu, para a maçã que muda de lugar
  const appleAgeMsRef = useRef(0);
  const nextDirectionRef = useRef<Direction>("RIGHT");
  const currentDirectionRef = useRef<Direction>("RIGHT");
  const growPendingRef = useRef(0);
  const matchIdRef = useRef<number | null>(null);
  const statusBeforeDialogRef = useRef<GameStatus>("PLAYING");
  const finishingRef = useRef(false);
  const startingRef = useRef(false);
  const dialogRef = useRef<"exit" | "howto" | null>(null);
  // Muda a cada partida e no fim dela: a resposta de um pedido feito antes é ignorada.
  const matchTokenRef = useRef(0);
  const remainingMsRef = useRef(FIRST_LEVEL.match_seconds * 1000);

  const changeStatus = useCallback((next: GameStatus) => {
    statusRef.current = next;
    setStatus(next);
  }, []);

  useEffect(() => {
    snakeRef.current = snake;
  }, [snake]);

  useEffect(() => {
    dialogRef.current = dialog;
  }, [dialog]);

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
    if (!authService.getCurrentUser()) return;
    setProgress(await progressService.getMyProgress());
  }, []);

  useEffect(() => {
    if (!currentUser) return;
    progressService.getMyProgress().then(setProgress);
    levelService.listLevels().then((list) => {
      if (list.length > 0) setLevels([...list].sort((a, b) => a.number - b.number));
    });
  }, [currentUser]);

  const maxLevels = levels.length;
  const levelConfig = (number: number) => levels.find((item) => item.number === number);
  const minScoreToAdvance = currentMatch?.level.min_score_to_advance ?? levelConfig(level)?.min_score_to_advance ?? 30;
  const errorCount = answers.filter((answer) => !answer.isCorrect).length;
  const blocksFromErrors = errorCount * rules.growth_per_error;
  const acertos = answers.length - errorCount;

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
  const currentLevel = progress.current_level;
  const latestRef = useRef({ level, matchDuration, timeLeft, score, answers, currentUser, currentLevel });
  useLayoutEffect(() => {
    latestRef.current = { level, matchDuration, timeLeft, score, answers, currentUser, currentLevel };
  });

  const finishMatch = useCallback(
    async (reason: MatchEndReason) => {
      if (finishingRef.current) return;
      finishingRef.current = true;
      matchTokenRef.current += 1;
      changeStatus("FINISHED");
      setDialog(null);

      const { level, matchDuration, timeLeft, score, answers, currentUser, currentLevel } = latestRef.current;
      const erros = answers.filter((answer) => !answer.isCorrect).length;
      const activeMatchId = matchIdRef.current;
      matchIdRef.current = null;
      let advanced = false;
      let unlockedLevel = level;
      if (activeMatchId) {
        try {
          const result = await matchService.finishMatch(activeMatchId, currentLevel);
          advanced = result.advanced;
          unlockedLevel = result.current_level;
        } catch (error) {
          console.error("Erro ao encerrar a partida na API:", error);
          setAppNotice(
            "Não foi possível salvar esta partida no servidor: os pontos dela podem não ter entrado no seu progresso."
          );
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
      // Um clique duplo (ou Enter repetido) não abre duas partidas
      if (startingRef.current) return;
      startingRef.current = true;
      let match: Match;
      try {
        match = await matchService.startMatch(levelNumber ?? progress.current_level);
      } catch (error) {
        // Sem a API não há partida: as perguntas e a correção vêm só dela.
        console.error("Erro ao iniciar a partida na API:", error);
        // A sessão expirada já leva ao login com o aviso
        if (authService.getCurrentUser()) {
          setAppNotice(errorText(error, "Não foi possível começar a partida. Tente de novo."));
          // O tutorial não mostra avisos: volta ao painel, onde ele aparece
          setCurrentScreen((screen) => (screen === "tutorial" ? "home" : screen));
        }
        return;
      } finally {
        startingRef.current = false;
      }
      if (!authService.getCurrentUser()) return; // a sessão expirou durante o pedido

      matchTokenRef.current += 1;
      finishingRef.current = false;
      growPendingRef.current = 0;
      setDialog(null);
      setEnding(null);
      setAppNotice(
        matchService.isLocalMatch(match.id) && !isGuestSession()
          ? "Servidor indisponível: esta partida é local e não vai para a sua conta."
          : null
      );

      const levelRules = match.level;
      const duration = match.duration_seconds;
      const boardSize = levelRules.board_size;
      const startSnake = initialSnake(boardSize);

      matchIdRef.current = match.id;
      setCurrentMatch(match);
      setLevel(levelRules.number);
      setRules(levelRules);
      rulesRef.current = levelRules;
      setMatchDuration(duration);
      setTimeLeft(duration);
      remainingMsRef.current = duration * 1000;
      setSnake(startSnake);
      snakeRef.current = startSnake;
      setDirection("RIGHT");
      nextDirectionRef.current = "RIGHT";
      currentDirectionRef.current = "RIGHT";
      const firstApple = randomFreeCell(boardSize, startSnake);
      setApple(firstApple);
      appleRef.current = firstApple;
      appleAgeMsRef.current = 0;
      setIsAppleFading(false);
      // Maçãs podres sorteadas uma a uma, cada uma numa célula ainda livre
      const firstRottenApples: Position[] = [];
      for (let index = 0; index < levelRules.rotten_apples; index++) {
        const cell = randomFreeCell(boardSize, [
          ...startSnake,
          ...(firstApple ? [firstApple] : []),
          ...firstRottenApples,
        ]);
        if (cell) firstRottenApples.push(cell);
      }
      setRottenApples(firstRottenApples);
      rottenApplesRef.current = firstRottenApples;
      setScore(0);
      setAnswers([]);
      setCurrentQuestion(null);
      setLastResult(null);
      setCurrentScreen("game");
      // A partida começa com a cobra andando; a contagem fica só para as retomadas
      changeStatus("PLAYING");
    },
    [progress.current_level, changeStatus]
  );

  const resumeWithCountdown = useCallback(() => {
    setCountdownLeft(COUNTDOWN_SECONDS);
    changeStatus("COUNTDOWN");
  }, [changeStatus]);

  // Status depois de um pedido à API. Com uma janela aberta (ex.: Sair), ele fica guardado
  // para quando ela fechar.
  const settleStatus = useCallback(
    (next: "PLAYING" | "FEEDBACK") => {
      if (dialogRef.current) statusBeforeDialogRef.current = next;
      else if (next === "PLAYING") resumeWithCountdown();
      else changeStatus(next);
    },
    [resumeWithCountdown, changeStatus]
  );

  const openQuestion = useCallback(async () => {
    const token = matchTokenRef.current;
    changeStatus("QUESTION");
    setCurrentQuestion(null);
    setLastResult(null);
    setReliability(INITIAL_RELIABILITY);
    setQuestionSecondsLeft(rulesRef.current.question_seconds);
    try {
      const question = await matchService.getNextQuestion(matchIdRef.current ?? 0);
      if (token !== matchTokenRef.current) return; // a partida acabou durante o pedido
      setCurrentQuestion(question);
    } catch (error) {
      if (token !== matchTokenRef.current) return;
      // 404: acabaram as afirmações; 422: a API não aceita mais perguntas nesta partida
      // (limite de respostas ou tempo de partida aberta).
      if (error instanceof HttpError && error.status === 404) {
        finishMatch("NO_QUESTIONS");
        return;
      }
      if (error instanceof HttpError && error.status === 422) {
        finishMatch("TIMEOUT");
        return;
      }
      console.error("Erro ao buscar a próxima afirmação:", error);
      settleStatus("PLAYING");
    }
  }, [changeStatus, finishMatch, settleStatus]);

  // Um passo da cobrinha
  const step = useCallback(() => {
    if (statusRef.current !== "PLAYING") return;

    const levelRules = rulesRef.current;
    const boardSize = levelRules.board_size;
    const currentSnake = snakeRef.current;
    const activeDirection = nextDirectionRef.current;
    currentDirectionRef.current = activeDirection;
    setDirection(activeDirection);

    const newHead = nextHead(currentSnake[0], activeDirection, boardSize, levelRules.solid_walls);
    // Bateu na parede sólida ou no próprio corpo
    if (!newHead || hitsBody(currentSnake, newHead, growPendingRef.current > 0)) {
      soundEffects.playGameOver();
      finishMatch("GAMEOVER");
      return;
    }

    const newSnake = [newHead, ...currentSnake];
    // A cobrinha só cresce depois de um erro (ou da maçã podre)
    if (growPendingRef.current > 0) {
      growPendingRef.current -= 1;
    } else {
      newSnake.pop();
    }
    snakeRef.current = newSnake;
    setSnake(newSnake);

    const occupiedExcept = (...others: (Position | null)[]) => [
      ...newSnake,
      ...others.filter((cell): cell is Position => cell !== null),
    ];
    const moveApple = () => {
      const nextApple = randomFreeCell(boardSize, occupiedExcept(...rottenApplesRef.current));
      appleRef.current = nextApple;
      setApple(nextApple);
      appleAgeMsRef.current = 0;
      setIsAppleFading(false);
    };

    const eatenRotten = rottenApplesRef.current.findIndex((rotten) => sameCell(newHead, rotten));
    if (eatenRotten >= 0) {
      soundEffects.playMistake();
      growPendingRef.current += ROTTEN_APPLE_GROWTH;
      // A maçã podre comida reaparece em outro lugar; as outras ficam onde estão
      const others = rottenApplesRef.current.filter((_, index) => index !== eatenRotten);
      const nextRotten = randomFreeCell(boardSize, occupiedExcept(appleRef.current, ...others));
      const nextRottenApples = nextRotten ? [...others, nextRotten] : others;
      rottenApplesRef.current = nextRottenApples;
      setRottenApples(nextRottenApples);
    }

    const currentApple = appleRef.current;
    if (currentApple && sameCell(newHead, currentApple)) {
      soundEffects.playEat();
      moveApple();
      openQuestion();
      return;
    }

    // Maçã com prazo: muda de lugar depois de um tempo de cobra andando e pisca antes
    const lifetimeMs = (levelRules.apple_lifetime_seconds ?? 0) * 1000;
    if (lifetimeMs > 0 && currentApple) {
      appleAgeMsRef.current += levelRules.tick_ms;
      if (appleAgeMsRef.current >= lifetimeMs) moveApple();
      else setIsAppleFading(lifetimeMs - appleAgeMsRef.current <= APPLE_FADING_MS);
    }
  }, [finishMatch, openQuestion]);

  // Mexer a cobra durante a contagem encerra a contagem e volta ao jogo na hora
  const changeDirection = useCallback(
    (next: Direction) => {
      const current = statusRef.current;
      if (current !== "PLAYING" && current !== "COUNTDOWN") return;
      if (OPPOSITE_DIRECTIONS[next] !== currentDirectionRef.current) nextDirectionRef.current = next;
      if (current === "COUNTDOWN") changeStatus("PLAYING");
    },
    [changeStatus]
  );

  // Loop da cobrinha
  useEffect(() => {
    if (currentScreen !== "game" || status !== "PLAYING") return;
    const timer = window.setInterval(step, rules.tick_ms);
    return () => window.clearInterval(timer);
  }, [currentScreen, status, rules.tick_ms, step]);

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
    const timer = window.setInterval(() => {
      consume();
      // O tempo acaba com a cobra andando; ao pausar, o resto só é descontado
      if (remainingMsRef.current <= 0) finishMatch("TIMEOUT");
    }, 200);
    return () => {
      window.clearInterval(timer);
      consume();
    };
  }, [currentScreen, status, finishMatch]);

  useEffect(() => {
    if (status === "PLAYING" && timeLeft > 0 && timeLeft <= 5) soundEffects.playTick();
  }, [timeLeft, status]);

  // Contagem de 3 s antes de a cobra andar
  useEffect(() => {
    if (currentScreen !== "game" || status !== "COUNTDOWN") return;
    const timer = window.setTimeout(() => {
      if (countdownLeft <= 1) changeStatus("PLAYING");
      else setCountdownLeft(countdownLeft - 1);
    }, 1000);
    return () => window.clearTimeout(timer);
  }, [currentScreen, status, countdownLeft, changeStatus]);

  // Trocar de aba pausa a partida: em segundo plano o cronômetro continuaria correndo.
  useEffect(() => {
    if (currentScreen !== "game") return;
    const handleVisibility = () => {
      const current = statusRef.current;
      if (document.hidden && (current === "PLAYING" || current === "COUNTDOWN")) changeStatus("PAUSED");
    };
    document.addEventListener("visibilitychange", handleVisibility);
    return () => document.removeEventListener("visibilitychange", handleVisibility);
  }, [currentScreen, changeStatus]);

  // ---------------------------------------------------------------- pergunta

  const confirmAnswer = useCallback(async () => {
    if (!currentQuestion || isSubmittingAnswer || statusRef.current !== "QUESTION") return;
    setIsSubmittingAnswer(true);
    const token = matchTokenRef.current;
    const question = currentQuestion;
    const value = clampReliability(reliability);
    try {
      const result = await matchService.answerQuestion(matchIdRef.current ?? 0, question.id, value);
      if (token !== matchTokenRef.current) return; // a partida acabou durante o pedido
      setLastResult(result);
      setScore(result.score); // placar oficial da API
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
        growPendingRef.current += rulesRef.current.growth_per_error;
      }
      settleStatus("FEEDBACK");
    } catch (error) {
      if (token !== matchTokenRef.current) return;
      // Sem a correção da API não há como avaliar: a pergunta sai sem pontuar nem penalizar.
      console.error("Erro ao enviar a resposta:", error);
      setCurrentQuestion(null);
      settleStatus("PLAYING");
    } finally {
      setIsSubmittingAnswer(false);
    }
  }, [currentQuestion, isSubmittingAnswer, reliability, settleStatus]);

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

  // Bateu a meta do nível atual: a partida termina depois do resultado da pergunta.
  // Rejogar um nível já vencido segue até o fim, como na regra de avanço da API.
  const continueAfterFeedback = useCallback(() => {
    setCurrentQuestion(null);
    setLastResult(null);
    if (level === progress.current_level && score >= minScoreToAdvance) finishMatch("GOAL");
    else resumeWithCountdown();
  }, [level, progress.current_level, score, minScoreToAdvance, finishMatch, resumeWithCountdown]);

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

      if (current === "PLAYING" || current === "COUNTDOWN") {
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
    setAppNotice(null);
    setUserStats(authService.getUserStats(user.username));
    setProgress(DEFAULT_PROGRESS);
    setCurrentUser(user);
    setCurrentScreen(authService.hasSeenTutorial(user.username) ? "home" : "tutorial");
  };

  const handleLogout = () => {
    authService.logout();
    // Nada do jogador anterior fica na tela até o próximo entrar
    setProgress(DEFAULT_PROGRESS);
    setUserStats(authService.getUserStats(""));
    setAppNotice(null);
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
    // Só o tutorial da primeira entrada leva direto ao jogo; aberto pelo painel, volta a ele.
    const isFirstTutorial = !!currentUser && !authService.hasSeenTutorial(currentUser.username);
    return (
      <div className="fako-app screen-tutorial">
        <TutorialScreen
          questionSeconds={FIRST_LEVEL.question_seconds}
          pointsPerCorrect={POINTS_PER_CORRECT}
          completeLabel={isFirstTutorial ? "Começar a Jogar →" : "Voltar ao painel →"}
          onComplete={() => {
            markTutorialSeen();
            if (isFirstTutorial) startGame();
            else setCurrentScreen("home");
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
            boardSize={rules.board_size}
            status={status}
            timeLeft={timeLeft}
            duration={matchDuration}
            score={score}
            exitDisabled={isSubmittingAnswer}
            onExit={() => openDialog("exit")}
          />

          {appNotice && <AppNotice message={appNotice} onClose={() => setAppNotice(null)} />}

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
              tolerance={rules.reliability_tolerance}
              growthPerError={rules.growth_per_error}
              wrongAnswerPenalty={rules.wrong_answer_penalty}
              canPlayNextLevel={
                level < maxLevels && (ending.advanced || level < progress.current_level)
              }
              onPlayAgain={() => startGame(level)}
              onPlayNextLevel={() => startGame(level + 1)}
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
              gridSize={rules.board_size}
              rottenApples={rottenApples}
              isAppleFading={isAppleFading}
              solidWalls={rules.solid_walls}
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
            tolerance={rules.reliability_tolerance}
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
            growthPerError={rules.growth_per_error}
            wrongAnswerPenalty={rules.wrong_answer_penalty}
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
            rules={rules}
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

        {appNotice && <AppNotice message={appNotice} onClose={() => setAppNotice(null)} />}

        {currentScreen === "journey" ? (
          <JourneyScreen
            levels={levels}
            currentLevel={progress.current_level}
            highestLevel={progress.highest_level}
            totalScore={progress.total_score}
            matchesPlayed={progress.matches_played}
            bestScoreInLevel={bestScoreInCurrentLevel}
            stats={userStats}
            isGuest={isGuestSession()}
            onPlayLevel={(number) => startGame(number)}
          />
        ) : (
          <HomeScreen
            username={currentUser.username}
            currentLevel={progress.current_level}
            maxLevels={maxLevels}
            missingPoints={missingPoints}
            matchSeconds={(levelConfig(progress.current_level) ?? FIRST_LEVEL).match_seconds}
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
