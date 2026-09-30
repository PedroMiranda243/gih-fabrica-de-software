/**
 * Endereço que não leva a tela nenhuma — H79.
 *
 * Até a Sprint 06, o endereço inválido era redirecionado ao painel sem aviso:
 * quem seguia um link quebrado, ou digitava errado, caía numa tela que não
 * pediu e sem saber por quê — e o endereço sumia da barra, sem deixar nem o
 * que corrigir. Agora a página diz o que aconteceu, mostra o endereço pedido e
 * oferece a volta. O menu continua ao lado, com as telas que a pessoa abre.
 */
import { useLocation } from "react-router-dom";

import EstadoVazio from "../componentes/EstadoVazio";

export default function NaoEncontrada() {
  const { pathname, search } = useLocation();

  return (
    <section className="painel" aria-label="Página não encontrada">
      <EstadoVazio
        titulo="Este endereço não leva a nenhuma tela"
        texto={`Não existe tela em ${pathname}${search}. O endereço pode ter sido digitado errado, ou o link está incompleto. As telas que você abre estão no menu ao lado.`}
        acao={{ para: "/", rotulo: "Ir para o início" }}
      />
    </section>
  );
}
