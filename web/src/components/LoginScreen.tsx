import React, { useState } from "react";
import { authService } from "../services/authService";
import { User } from "../types";
import fakoSnakeImg from "../assets/fako-snake.png";
import { FakoLogo } from "./FakoLogo";

interface LoginScreenProps {
  onLoginSuccess: (user: User) => void;
  theme: "light" | "dark";
  onToggleTheme: () => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({
  onLoginSuccess,
  theme,
  onToggleTheme,
}) => {
  const [tab, setTab] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [isAccordionOpen, setIsAccordionOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [infoNotice, setInfoNotice] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfoNotice(null);

    if (!username.trim()) {
      setError("Por favor, digite seu nome de usuário.");
      return;
    }
    if (!password.trim()) {
      setError("Por favor, digite sua senha.");
      return;
    }
    if (tab === "register" && password.trim().length < 6) {
      setError("A senha deve ter pelo menos 6 caracteres.");
      return;
    }

    setIsLoading(true);

    try {
      if (tab === "login") {
        const result = await authService.login(username.trim(), password);
        if (result.success && result.user) {
          onLoginSuccess(result.user);
        } else {
          setError(result.error || "Nome de usuário ou senha incorretos.");
        }
      } else {
        const result = await authService.register(username.trim(), password);
        if (result.success && result.user) {
          onLoginSuccess(result.user);
        } else {
          setError(result.error || "Não foi possível criar a conta.");
        }
      }
    } catch {
      setError("Ocorreu um erro inesperado. Tente novamente.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleGuestLogin = async () => {
    setError(null);
    setInfoNotice(null);
    setIsLoading(true);
    try {
      const result = await authService.loginAsGuest();
      if (result.success && result.user) {
        onLoginSuccess(result.user);
      } else {
        setError("Não foi possível entrar como visitante.");
      }
    } catch {
      setError("Erro ao acessar como visitante.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleForgotPassword = () => {
    setError(null);
    setInfoNotice(
      "Para este ambiente de testes, acesse como visitante ou cadastre uma nova conta na aba 'Criar conta'."
    );
  };

  return (
    <main className="fako-auth-viewport">
      <div className="fako-auth-card">
        {/* ================= PAINEL ESQUERDO: IDENTIDADE VISUAL ================= */}
        <section className="fako-brand-panel" aria-label="Identidade FAKO">
          {/* Topo: Logo FAKO (3 quadrados da cobrinha + 1 maçã circular + texto FAKO em branco) */}
          <header className="fako-brand-header">
            <FakoLogo size="large" textColor="#ffffff" />
          </header>

          {/* Título Principal com hierarquia estrita */}
          <div className="fako-brand-body">
            <h1 className="fako-main-headline">
              <span className="headline-row">Jogue.</span>
              <span className="headline-row">Analise.</span>
              <span className="headline-row headline-accent">Aprenda.</span>
            </h1>

            {/* Texto Pedagógico Principal */}
            <p className="fako-hero-description">
              Guie a cobrinha, colete maçãs e descubra o nível de confiabilidade de cada notícia.
            </p>

            {/* Linha Divisória Minimalista */}
            <div className="fako-brand-bar" aria-hidden="true" />

            {/* Mensagem Complementar */}
            <div className="fako-complementary-msg">
              <p>Aprenda a analisar informações.</p>
              <p>Questione antes de compartilhar.</p>
            </div>
          </div>

          {/* Ilustração: Cobrinha FAKO Fiel à Imagem */}
          <div className="fako-illustration-area" aria-hidden="true">
            <img
              src={fakoSnakeImg}
              alt="Cobrinha e Maçã do FAKO"
              className="fako-snake-img"
              loading="eager"
            />
          </div>
        </section>

        {/* ================= PAINEL DIREITO: EXPERIÊNCIA DE ACESSO ================= */}
        <section className="fako-form-panel" aria-label="Acesso e Autenticação">
          {/* Barra Superior: Abas e Controle de Tema */}
          <div className="fako-top-toolbar">
            {/* Abas Superiores Pílula: Entrar | Criar conta */}
            <div className="fako-tabs-pill" role="tablist" aria-label="Opções de autenticação">
              <button
                type="button"
                role="tab"
                id="fako-tab-login"
                aria-selected={tab === "login"}
                aria-controls="fako-auth-form"
                className={`tab-pill-btn ${tab === "login" ? "active" : ""}`}
                onClick={() => {
                  setTab("login");
                  setError(null);
                  setInfoNotice(null);
                }}
              >
                Entrar
              </button>
              <button
                type="button"
                role="tab"
                id="fako-tab-register"
                aria-selected={tab === "register"}
                aria-controls="fako-auth-form"
                className={`tab-pill-btn ${tab === "register" ? "active" : ""}`}
                onClick={() => {
                  setTab("register");
                  setError(null);
                  setInfoNotice(null);
                }}
              >
                Criar conta
              </button>
            </div>

            {/* Alternador de Tema: Sol | Chave Switch | Lua */}
            <div className="fako-theme-switch-wrap">
              <button
                type="button"
                className="fako-theme-toggle-btn"
                role="switch"
                aria-checked={theme === "dark"}
                onClick={onToggleTheme}
                title={`Alternar para tema ${theme === "light" ? "escuro" : "claro"}`}
                aria-label={`Alternar para tema ${theme === "light" ? "escuro" : "claro"}`}
              >
                {/* Ícone de Sol */}
                <svg
                  viewBox="0 0 24 24"
                  className={`theme-icon sun-icon ${theme === "light" ? "active" : ""}`}
                  aria-hidden="true"
                >
                  <circle cx="12" cy="12" r="4" fill="currentColor" />
                  <path
                    d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41m14.14-14.14l-1.41 1.41"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                </svg>

                {/* Cápsula deslizante */}
                <span className="theme-toggle-track">
                  <span className={`theme-toggle-thumb ${theme === "dark" ? "checked" : ""}`} />
                </span>

                {/* Ícone de Lua */}
                <svg
                  viewBox="0 0 24 24"
                  className={`theme-icon moon-icon ${theme === "dark" ? "active" : ""}`}
                  aria-hidden="true"
                >
                  <path
                    d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"
                    fill="currentColor"
                  />
                </svg>
              </button>
            </div>
          </div>

          {/* Saudação e Boas-Vindas */}
          <div className="fako-greeting-block">
            <h2 className="greeting-title">
              {tab === "login" ? "Bem-vindo ao FAKO! 👋" : "Crie sua conta no FAKO! 🚀"}
            </h2>
            <p className="greeting-subtitle">
              {tab === "login"
                ? "Entre para continuar sua jornada de onde parou."
                : "Cadastre seu usuário e senha para salvar seu progresso."}
            </p>
          </div>

          {/* Feedback de Notificação Informativa */}
          {infoNotice && (
            <div className="fako-notice-banner" role="status">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
              <span>{infoNotice}</span>
            </div>
          )}

          {/* Feedback de Erro Acessível */}
          {error && (
            <div className="fako-error-banner" role="alert" aria-live="assertive">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          {/* Formulário Principal */}
          <form
            id="fako-auth-form"
            className="fako-auth-form"
            onSubmit={handleSubmit}
            noValidate
          >
            {/* Campo: Nome de usuário */}
            <div className="fako-field-group">
              <label htmlFor="fako-input-username" className="fako-field-label">
                Nome de usuário
              </label>
              <div className="fako-input-container">
                <span className="input-icon-slot" aria-hidden="true">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </span>
                <input
                  id="fako-input-username"
                  type="text"
                  className="fako-input-element"
                  placeholder="Digite seu usuário"
                  value={username}
                  onChange={(e) => {
                    setUsername(e.target.value);
                    if (error) setError(null);
                  }}
                  autoComplete="username"
                  required
                />
              </div>
            </div>

            {/* Campo: Senha */}
            <div className="fako-field-group">
              <label htmlFor="fako-input-password" className="fako-field-label">
                Senha
              </label>
              <div className="fako-input-container">
                <span className="input-icon-slot" aria-hidden="true">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                </span>
                <input
                  id="fako-input-password"
                  type={showPassword ? "text" : "password"}
                  className="fako-input-element"
                  placeholder="Digite sua senha"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (error) setError(null);
                  }}
                  autoComplete={tab === "login" ? "current-password" : "new-password"}
                  required
                />
                <button
                  type="button"
                  className="fako-password-toggle-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Ocultar senha" : "Exibir senha em texto claro"}
                >
                  {showPassword ? (
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {/* Linha Auxiliar: Lembrar de mim e Esqueceu sua senha? */}
            <div className="fako-form-options-row">
              <label className="fako-checkbox-control">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="fako-checkbox-input"
                />
                <span className="fako-checkbox-custom" aria-hidden="true" />
                <span className="fako-checkbox-text">Lembrar de mim</span>
              </label>

              <button
                type="button"
                className="fako-forgot-password-link"
                onClick={handleForgotPassword}
              >
                Esqueceu sua senha?
              </button>
            </div>

            {/* Botão Primário: Entrar (Elemento visualmente mais importante) */}
            <button
              type="submit"
              className="fako-primary-cta-btn"
              disabled={isLoading}
            >
              {isLoading ? (
                <span className="fako-btn-spinner-wrap">
                  <span className="fako-btn-spinner" aria-hidden="true" />
                  <span>Carregando...</span>
                </span>
              ) : tab === "login" ? (
                "Entrar"
              ) : (
                "Criar conta"
              )}
            </button>
          </form>

          {/* Divisor "ou" */}
          <div className="fako-auth-divider" aria-hidden="true">
            <span className="divider-line" />
            <span className="divider-label">ou</span>
            <span className="divider-line" />
          </div>

          {/* Link Secundário: Continuar como visitante */}
          <div className="fako-guest-action-block">
            <button
              type="button"
              className="fako-guest-link"
              onClick={handleGuestLogin}
              disabled={isLoading}
            >
              <span>Continuar como visitante</span>
              <span className="guest-arrow" aria-hidden="true">→</span>
            </button>
          </div>

          {/* Componente Expansível: Como funciona? */}
          <div className="fako-accordion-module">
            <button
              type="button"
              className="fako-accordion-trigger"
              onClick={() => setIsAccordionOpen(!isAccordionOpen)}
              aria-expanded={isAccordionOpen}
              aria-controls="fako-accordion-explanation"
            >
              <span className="fako-accordion-label-group">
                <svg
                  viewBox="0 0 24 24"
                  width="18"
                  height="18"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="fako-info-icon"
                  aria-hidden="true"
                >
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="16" x2="12" y2="12" />
                  <line x1="12" y1="8" x2="12.01" y2="8" />
                </svg>
                <span className="accordion-heading-text">Como funciona?</span>
              </span>
              <svg
                viewBox="0 0 24 24"
                width="18"
                height="18"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className={`fako-chevron-icon ${isAccordionOpen ? "expanded" : ""}`}
                aria-hidden="true"
              >
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </button>

            <div
              id="fako-accordion-explanation"
              className={`fako-accordion-content ${isAccordionOpen ? "open" : ""}`}
              role="region"
              aria-hidden={!isAccordionOpen}
            >
              <div className="fako-accordion-inner">
                <p>
                  O FAKO utiliza inteligência artificial para analisar padrões presentes nas notícias.
                  O resultado é uma estimativa de confiabilidade, e não uma confirmação da veracidade da informação.
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
};
