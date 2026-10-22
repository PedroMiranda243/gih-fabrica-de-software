/**
 * O portal do parceiro: o histórico dele, e nada da rede — sem ranking, sem
 * posição, sem comparação com outros. De quem é, quem diz é o servidor.
 */
import { api } from "../api/cliente";
import { useCarregar } from "../api/ganchos";
import { Ausente, Dinheiro, Variacao } from "../componentes/Dados";
import { Carregando, ErroDaTela, Nota, Vazio } from "../componentes/Estados";
import Kpi from "../componentes/Kpi";
import Serie from "../componentes/Serie";
import { useTitulo } from "../componentes/Titulo";
import { comoDiaMes, comoInteiro, comoPeriodo } from "../formato";

export default function MeuDesempenho() {
  useTitulo("Meu desempenho");
  const meu = useCarregar(() => api.get("/api/meu-desempenho"), "meu");

  if (meu.carregando) return <Carregando rotulo="Carregando o seu desempenho" linhas={6} />;
  if (meu.erro) return <ErroDaTela erro={meu.erro} />;
  const d = meu.dados;

  if (!d.pontos.length) {
    return (
      <div className="pagina">
        <Vazio titulo={`${d.parceiro}: seus números ainda não chegaram.`} icone="relogio">
          Eles aparecem aqui depois da primeira importação de relatório que incluir o seu comércio.
        </Vazio>
      </div>
    );
  }

  const periodoAtual = d.atual?.periodo ?? d.pontos[d.pontos.length - 1].periodo;
  const semValoresNoAtual = d.atual && d.atual.faturamento === null;
  const primeiro = !d.anterior;

  return (
    <div className="pagina pagina--portal">
      <header className="portal-cabeca">
        <p className="portal-cabeca__nome">{d.parceiro}</p>
        {d.categoria && <p className="portal-cabeca__categoria">{d.categoria}</p>}
        <p className="portal-cabeca__nota">
          Período de {comoPeriodo(periodoAtual)}
          {primeiro ? " — o primeiro com os seus números" : `, comparado com ${comoPeriodo(d.anterior)}`}. Só os seus números: nenhum outro parceiro aparece aqui.
        </p>
      </header>

      {semValoresNoAtual && (
        <Nota tipo="atencao" papel="status">
          O último relatório não trouxe o seu comércio. Os indicadores do período ficam vazios, e o gráfico mostra a falta como um intervalo, e não como zero.
        </Nota>
      )}
      {primeiro && !semValoresNoAtual && (
        <Nota>Este é o primeiro período com os seus números: ainda não há com o que comparar. A variação aparece a partir do próximo relatório.</Nota>
      )}

      <section className="faixa-kpi faixa-kpi--tres" aria-labelledby="titulo-meus-indicadores">
        <h2 id="titulo-meus-indicadores" className="sr-only">
          Seus indicadores do período mais recente
        </h2>
        <div className="faixa-kpi__grade">
          <Kpi rotulo="Faturamento" principal selo={`${comoDiaMes(periodoAtual.data_inicio)} – ${comoDiaMes(periodoAtual.data_fim)}`} variacao={<Variacao valor={d.variacao?.faturamento} semBase="Sem período anterior seu para comparar" />}>
            <Dinheiro valor={d.atual?.faturamento} grande porque="o último relatório não trouxe o seu comércio" />
          </Kpi>
          <Kpi rotulo="Pedidos" variacao={<Variacao valor={d.variacao?.pedidos} semBase="Sem período anterior seu para comparar" />}>
            {d.atual?.pedidos === null || d.atual?.pedidos === undefined ? <Ausente porque="o último relatório não trouxe o seu comércio" /> : comoInteiro(d.atual.pedidos)}
          </Kpi>
          <Kpi rotulo="Ticket médio" variacao={<Variacao valor={d.variacao?.ticket_medio} semBase="Sem período anterior seu para comparar" />}>
            <Dinheiro valor={d.atual?.ticket_medio} grande porque="o último relatório não trouxe o seu comércio" />
          </Kpi>
        </div>
      </section>

      <section className="bloco bloco--serie" aria-labelledby="titulo-meu-faturamento">
        <div className="bloco__cabeca">
          <h2 id="titulo-meu-faturamento" className="bloco__titulo">
            Seu faturamento
          </h2>
          <p className="bloco__sub">Período a período, desde a sua primeira medição</p>
        </div>
        <Serie pontos={d.pontos} rotulo="Seu faturamento" altura={300} />
      </section>
    </div>
  );
}
