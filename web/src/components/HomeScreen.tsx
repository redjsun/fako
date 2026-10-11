import React from "react";
import { User, UserStats, QuestionCategory } from "../types";
import { FakoLogo } from "./FakoLogo";

export interface HomeScreenProps {
  user: User;
  stats: UserStats;
  onPlay: () => void;
  onSelectCategory?: (cat: QuestionCategory | "Misto") => void;
  onCategories: () => void;
  onTutorial: () => void;
  onJourney: () => void;
  onLogout: () => void;
  isMuted: boolean;
  onToggleMute: () => void;
  theme: "light" | "dark";
  onToggleTheme: () => void;
}

/**
 * Mini-tabuleiro plano da Cobrinha idêntico ao GameBoard.tsx:
 * - Grade suave em verde claro (#eaf3e8 e linhas #c2dec0)
 * - Cobrinha oficial com cantos arredondados, cabeça #1d4a27 e olhos expressivos
 * - Maçã oficial com cabinho de madeira, folha verde e brilho
 */
const HomeSnakeBoardVisual: React.FC = () => {
  return (
    <div className="hero-board-side" aria-hidden="true">
      <div className="hero-mini-board">
        <svg
          viewBox="0 0 216 148"
          className="hero-board-svg"
          xmlns="http://www.w3.org/2000/svg"
          aria-label="Cobrinha do FAKO no tabuleiro"
        >
          <defs>
            <pattern
              id="homeHeroBoardGrid"
              width="24"
              height="24"
              patternUnits="userSpaceOnUse"
            >
              <path
                d="M 24 0 L 0 0 0 24"
                fill="none"
                stroke="rgba(47, 107, 58, 0.16)"
                strokeWidth="1.2"
              />
            </pattern>
          </defs>

          {/* Fundo do Mini-Tabuleiro plano com cantos suaves */}
          <rect width="216" height="148" rx="16" fill="#eaf3e8" />
          <rect width="216" height="148" rx="16" fill="url(#homeHeroBoardGrid)" />
          <rect
            width="216"
            height="148"
            rx="16"
            fill="none"
            stroke="#c2dec0"
            strokeWidth="1.6"
          />

          {/* 1. CORPO DA COBRINHA (3 segmentos verdes idênticos ao GameBoard.tsx) */}
          {[28, 52, 76].map((x, i) => (
            <g key={i}>
              <rect
                x={x}
                y={86}
                width={20}
                height={20}
                rx={5}
                fill="#2f6b3a"
              />
              {/* Brilho orgânico suave no topo de cada bloco */}
              <rect
                x={x + 1.5}
                y={88}
                width={17}
                height={6}
                rx={2.5}
                fill="rgba(255, 255, 255, 0.14)"
              />
            </g>
          ))}

          {/* 2. CABEÇA DA COBRINHA (#1d4a27 arredondada) */}
          <rect
            x={100}
            y={86}
            width={21}
            height={20}
            rx={6.5}
            fill="#1d4a27"
          />

          {/* 3. OLHOS EXPRESSIVOS (olhando para a direita/maçã) */}
          {/* Olho Superior */}
          <circle cx={113} cy={91.5} r={3} fill="#ffffff" />
          <circle cx={114.2} cy={91.5} r={1.5} fill="#111a13" />
          <circle cx={113.8} cy={91} r={0.6} fill="#ffffff" />

          {/* Olho Inferior */}
          <circle cx={113} cy={100.5} r={3} fill="#ffffff" />
          <circle cx={114.2} cy={100.5} r={1.5} fill="#111a13" />
          <circle cx={113.8} cy={100} r={0.6} fill="#ffffff" />

          {/* 4. MAÇÃ OFICIAL DO JOGO */}
          {/* Sombra da Maçã */}
          <ellipse
            cx={174}
            cy={110}
            rx={11}
            ry={3.2}
            fill="rgba(0, 0, 0, 0.12)"
          />
          {/* Corpo Vermelho */}
          <circle cx={174} cy={97} r={12} fill="#dc3545" />
          {/* Brilho */}
          <ellipse
            cx={170}
            cy={93}
            rx={3.8}
            ry={2.2}
            transform="rotate(-35 170 93)"
            fill="rgba(255, 255, 255, 0.42)"
          />
          {/* Cabinho de Madeira */}
          <path
            d="M 174 85 C 173 80, 172 77, 177 74"
            fill="none"
            stroke="#5a3d28"
            strokeWidth="2"
            strokeLinecap="round"
          />
          {/* Folha Verde */}
          <ellipse
            cx={180}
            cy={76}
            rx={3.8}
            ry={2}
            transform="rotate(25 180 76)"
            fill="#2f6b3a"
          />
        </svg>
      </div>
    </div>
  );
};

export const HomeScreen: React.FC<HomeScreenProps> = ({
  user,
  stats,
  onPlay,
  onSelectCategory,
  onTutorial,
  onJourney,
  onLogout,
  isMuted,
  onToggleMute,
  theme,
  onToggleTheme,
}) => {
  // Cálculo de precisão ou fallback pedagógico
  const totalChecks = stats.totalAcertos + stats.totalErros;
  const accuracyPercentage =
    totalChecks > 0 ? Math.round((stats.totalAcertos / totalChecks) * 100) : 78;
  const displayScore = stats.highScore > 0 ? stats.highScore : 240;
  const displayGames = stats.gamesPlayed > 0 ? stats.gamesPlayed : 12;
  const currentLevel = Math.min(6, Math.max(1, stats.maxLevel || 3));

  const handleCategoryClick = (cat: QuestionCategory) => {
    if (onSelectCategory) {
      onSelectCategory(cat);
    } else {
      onPlay();
    }
  };

  return (
    <div className="figma-home-wrapper">
      {/* ================= BARRA DE NAVEGAÇÃO SUPERIOR (FIGMA) ================= */}
      <header className="figma-home-topbar">
        {/* Logo FAKO Oficial (3 segmentos + maçã + FAKO) */}
        <div className="figma-nav-left">
          <FakoLogo size="medium" textColor={theme === "dark" ? "#ffffff" : "#112a17"} />
        </div>

        {/* Links Centrais em Pílula */}
        <nav className="figma-nav-center" aria-label="Navegação Principal">
          <button
            type="button"
            className="nav-link-pill active"
            aria-current="page"
          >
            Início
          </button>
          <button
            type="button"
            className="nav-link-pill"
            onClick={onTutorial}
          >
            Tutorial
          </button>
          <button
            type="button"
            className="nav-link-pill"
            onClick={onJourney}
          >
            Jornada
          </button>
        </nav>

        {/* Lado Direito: Perfil do Usuário e Controles */}
        <div className="figma-nav-right">
          {/* Badge de Perfil com Avatar e Nome do Usuário */}
          <div className="figma-user-chip" title={`Logado como ${user.username}`}>
            <div className="user-avatar-gold">
              {user.username.charAt(0).toUpperCase()}
            </div>
            <div className="user-chip-texts">
              <span className="user-chip-name">{user.username}</span>
              <span className="user-chip-details">
                Nível {currentLevel} • {displayScore} pts
              </span>
            </div>
          </div>

          {/* Controles de Som, Tema Estrito e Logout */}
          <div className="figma-quick-controls">
            <button
              type="button"
              className="figma-control-icon-btn"
              onClick={onToggleTheme}
              title={`Alternar para tema ${theme === "light" ? "escuro" : "claro"}`}
              aria-label="Alternar tema claro/escuro"
            >
              {theme === "dark" ? "🌙" : "☀️"}
            </button>

            <button
              type="button"
              className="figma-control-icon-btn"
              onClick={onToggleMute}
              title={isMuted ? "Ativar som" : "Desativar som"}
              aria-label={isMuted ? "Ativar som" : "Desativar som"}
            >
              {isMuted ? "🔇" : "🔊"}
            </button>

            <button
              type="button"
              className="figma-control-icon-btn logout"
              onClick={onLogout}
              title="Sair da conta"
              aria-label="Sair da conta"
            >
              🚪
            </button>
          </div>
        </div>
      </header>

      {/* ================= GRID PRINCIPAL EM 2 COLUNAS (FIGMA SCREEN 02) ================= */}
      <main className="figma-home-grid">
        {/* ================= COLUNA ESQUERDA (PRINCIPAL) ================= */}
        <div className="figma-main-column">
          {/* 1. Hero Card Verde (#2BA84A) */}
          <section className="figma-hero-banner" aria-label="Ação rápida">
            <div className="hero-text-side">
              <div className="hero-user-tag">
                <span>Olá, {user.username}! 🌿</span>
              </div>

              <h1 className="hero-headline-title">
                Pronto para caçar algumas fakes hoje?
              </h1>

              <p className="hero-headline-desc">
                Partidas de 120 segundos. Cada maçã traz uma informação para você analisar.
              </p>

              <div className="hero-button-row">
                <button
                  type="button"
                  className="hero-primary-btn"
                  onClick={onPlay}
                >
                  Jogar agora ➔
                </button>
                <button
                  type="button"
                  className="hero-secondary-btn"
                  onClick={onTutorial}
                >
                  Como jogar
                </button>
              </div>
            </div>

            {/* Mini Tabuleiro da Cobrinha Plano */}
            <HomeSnakeBoardVisual />
          </section>

          {/* 2. Seção: Categorias das informações */}
          <section className="figma-categories-section">
            <div className="categories-header-row">
              <h2 className="categories-title">Categorias das informações</h2>
              <span className="categories-validation-badge">
                Validadas antes de chegar até você ✓
              </span>
            </div>

            <div className="categories-cards-trio">
              {/* Card 1: Saúde */}
              <div
                className="category-white-card cat-saude"
                onClick={() => handleCategoryClick("Saúde")}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === "Enter" && handleCategoryClick("Saúde")}
              >
                <div className="cat-icon-circle saude">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#135128" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
                    <path d="M12 7.5v5M9.5 10h5" strokeWidth="2" />
                  </svg>
                </div>
                <h3 className="cat-card-title saude-title">Saúde</h3>
                <p className="cat-card-desc">
                  Mitos e fatos sobre corpo, vacinas e bem-estar.
                </p>
              </div>

              {/* Card 2: Tecnologia */}
              <div
                className="category-white-card cat-tecnologia"
                onClick={() => handleCategoryClick("Tecnologia")}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === "Enter" && handleCategoryClick("Tecnologia")}
              >
                <div className="cat-icon-circle tecnologia">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#135128" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <rect x="2" y="3" width="20" height="14" rx="2" />
                    <path d="M8 21h8M12 17v4" />
                  </svg>
                </div>
                <h3 className="cat-card-title tecnologia-title">Tecnologia</h3>
                <p className="cat-card-desc">
                  Golpes, IA, redes sociais e o mundo digital.
                </p>
              </div>

              {/* Card 3: Conhecimentos Gerais */}
              <div
                className="category-white-card cat-gerais"
                onClick={() => handleCategoryClick("Conhecimentos Gerais")}
                role="button"
                tabIndex={0}
                onKeyDown={(e) =>
                  e.key === "Enter" && handleCategoryClick("Conhecimentos Gerais")
                }
              >
                <div className="cat-icon-circle gerais">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#135128" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <circle cx="12" cy="12" r="10" />
                    <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20M2 12h20" />
                  </svg>
                </div>
                <h3 className="cat-card-title gerais-title">Conhecimentos Gerais</h3>
                <p className="cat-card-desc">
                  História, ciência e curiosidades do mundo.
                </p>
              </div>
            </div>
          </section>

          {/* 3. Card Escuro: Como o FAKO funciona */}
          <section className="figma-flow-card" aria-label="Como funciona o jogo">
            <h3 className="flow-card-heading">Como o FAKO funciona</h3>
            <div className="flow-steps-track">
              <div className="flow-step-item">
                <span className="step-icon">🎮</span>
                <span className="step-label">Jogar</span>
              </div>
              <span className="flow-arrow-separator">➔</span>

              <div className="flow-step-item">
                <span className="step-icon">🍎</span>
                <span className="step-label">Coletar</span>
              </div>
              <span className="flow-arrow-separator">➔</span>

              <div className="flow-step-item">
                <span className="step-icon">🔍</span>
                <span className="step-label">Avaliar</span>
              </div>
              <span className="flow-arrow-separator">➔</span>

              <div className="flow-step-item">
                <span className="step-icon">💬</span>
                <span className="step-label">Feedback</span>
              </div>
            </div>
          </section>
        </div>

        {/* ================= COLUNA DIREITA (TELEMETRIA & HISTÓRICO) ================= */}
        <aside className="figma-sidebar-column">
          {/* Card: Sua jornada */}
          <div className="figma-side-card journey-card">
            <div className="side-card-top-header">
              <h3 className="side-card-heading">Sua jornada</h3>
              <span className="journey-level-tag">
                Nível {currentLevel} de 6
              </span>
            </div>

            {/* Trilha de 6 Níveis em Círculos */}
            <div className="journey-level-steps" aria-label="Progresso nos níveis">
              {[1, 2, 3, 4, 5, 6].map((lvl) => {
                const isCompleted = lvl < currentLevel;
                const isCurrent = lvl === currentLevel;
                return (
                  <div
                    key={lvl}
                    className={`level-step-circle ${
                      isCompleted ? "completed" : isCurrent ? "current" : "locked"
                    }`}
                    title={`Nível ${lvl} ${
                      isCompleted ? "(Concluído)" : isCurrent ? "(Atual)" : "(Bloqueado)"
                    }`}
                  >
                    {isCompleted ? "✓" : lvl}
                  </div>
                );
              })}
            </div>

            {/* Faixa explicativa do tamanho do tabuleiro */}
            <div className="journey-grid-info-pill">
              <span className="info-check">✓</span>
              <span>Tabuleiro clássico 16×16 • 6 níveis progressivos</span>
            </div>
          </div>

          {/* Grid de 3 Métricas Rápidas */}
          <div className="figma-stats-trio-row">
            <div className="stat-metric-box">
              <span className="metric-large-number">{displayScore}</span>
              <span className="metric-sub-label">Melhor pontuação</span>
            </div>

            <div className="stat-metric-box">
              <span className="metric-large-number">{accuracyPercentage}%</span>
              <span className="metric-sub-label">Taxa de acertos</span>
            </div>

            <div className="stat-metric-box">
              <span className="metric-large-number">{displayGames}</span>
              <span className="metric-sub-label">Partidas jogadas</span>
            </div>
          </div>

          {/* Card: Última partida */}
          <div className="figma-side-card last-match-card">
            <h3 className="side-card-heading">Última partida</h3>

            <div className="last-match-facts-list">
              {/* Item 1 */}
              <div className="fact-item-row">
                <div className="fact-item-icon check-green">✓</div>
                <div className="fact-item-body">
                  <span className="fact-statement">Vacinas causam autismo.</span>
                  <span className="fact-tagline">Não confiável • Saúde</span>
                </div>
                <span className="fact-status-badge badge-hit">
                  Confiável <span className="status-badge-icon">✓</span>
                </span>
              </div>

              {/* Item 2 */}
              <div className="fact-item-row">
                <div className="fact-item-icon cross-red">✕</div>
                <div className="fact-item-body">
                  <span className="fact-statement">
                    A Muralha da China é visível do espaço a olho nu.
                  </span>
                  <span className="fact-tagline">Não confiável • Conh. Gerais</span>
                </div>
                <span className="fact-status-badge badge-miss">
                  Não confiável <span className="status-badge-icon">✕</span>
                </span>
              </div>

              {/* Item 3 */}
              <div className="fact-item-row">
                <div className="fact-item-icon check-green">✓</div>
                <div className="fact-item-body">
                  <span className="fact-statement">
                    Senhas longas são mais seguras que senhas curtas.
                  </span>
                  <span className="fact-tagline">Confiável • Tecnologia</span>
                </div>
                <span className="fact-status-badge badge-hit">
                  Confiável <span className="status-badge-icon">✓</span>
                </span>
              </div>
            </div>
          </div>
        </aside>
      </main>
    </div>
  );
};
