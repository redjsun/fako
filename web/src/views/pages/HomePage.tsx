// Camada de visão: apenas renderiza o que o controller entrega.
import { useHealth } from "../../controllers/useHealth";

export default function HomePage() {
  const { health, erro } = useHealth();

  return (
    <main>
      <h1>Cobrinha Fake News</h1>
      <p>Projeto inicializado.</p>
      <p>API: {erro ?? health?.status ?? "carregando..."}</p>
    </main>
  );
}
