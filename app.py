# ============================================================
#  REALOCA — protótipo de realocação de hóspedes (overbooking)
#  Para rodar:  streamlit run app.py
# ============================================================

import math
import random
from datetime import date, timedelta

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Realoca", page_icon="🏨", layout="wide")


# ------------------------------------------------------------
# 1. DADOS INICIAIS (hotéis fictícios da rede de parceiros)
#    x e y = posição no "mapa", em km
#    preco_parceiro = valor combinado antes entre os hotéis
#    chance_aceite = chance de o hotel aceitar o pedido (simulação)
# ------------------------------------------------------------
def hoteis_iniciais():
    return [
        {"nome": "Hotel Atlântico", "estrelas": 4, "x": 0.0, "y": 0.0,
         "preco_parceiro": 300, "chance_aceite": 0.0,
         "vagas": {"Solteiro": 0, "Casal": 0, "Família": 0}},
        {"nome": "Pousada Maré Alta", "estrelas": 3, "x": 1.2, "y": 0.8,
         "preco_parceiro": 190, "chance_aceite": 0.9,
         "vagas": {"Solteiro": 2, "Casal": 3, "Família": 0}},
        {"nome": "Hotel Coral Plaza", "estrelas": 4, "x": 2.0, "y": -1.0,
         "preco_parceiro": 280, "chance_aceite": 0.7,
         "vagas": {"Solteiro": 1, "Casal": 2, "Família": 1}},
        {"nome": "Grand Recifes Hotel", "estrelas": 5, "x": -1.5, "y": 2.5,
         "preco_parceiro": 420, "chance_aceite": 0.6,
         "vagas": {"Solteiro": 0, "Casal": 1, "Família": 2}},
        {"nome": "Hotel Brisa Mar", "estrelas": 4, "x": 3.5, "y": 3.0,
         "preco_parceiro": 260, "chance_aceite": 0.8,
         "vagas": {"Solteiro": 3, "Casal": 4, "Família": 1}},
        {"nome": "Palace Oceano", "estrelas": 5, "x": 6.0, "y": -4.0,
         "preco_parceiro": 450, "chance_aceite": 0.5,
         "vagas": {"Solteiro": 2, "Casal": 2, "Família": 2}},
    ]


# Guarda os dados enquanto o app estiver aberto
if "hoteis" not in st.session_state:
    st.session_state.hoteis = hoteis_iniciais()
    st.session_state.historico = []
    st.session_state.resultado = None


# ------------------------------------------------------------
# 2. FUNÇÕES (as "regras" do app)
# ------------------------------------------------------------
def achar_hotel(nome):
    for h in st.session_state.hoteis:
        if h["nome"] == nome:
            return h
    return None


def distancia_km(a, b):
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def buscar_candidatos(origem, tipo_quarto, raio_km):
    """Filtra hotéis parceiros: mesma categoria ou superior, com vaga e dentro do raio."""
    candidatos = []
    for h in st.session_state.hoteis:
        if h["nome"] == origem["nome"]:
            continue
        if h["estrelas"] < origem["estrelas"]:
            continue
        if h["vagas"][tipo_quarto] <= 0:
            continue
        d = distancia_km(origem, h)
        if d > raio_km:
            continue
        candidatos.append({"hotel": h, "distancia": round(d, 1)})
    candidatos.sort(key=lambda c: c["distancia"])
    return candidatos


def disparar_pedido(candidatos):
    """Simula o envio do pedido: cada hotel aceita ou recusa, em um tempo aleatório.
    Ganha o primeiro que aceitar."""
    respostas = []
    for c in candidatos:
        aceitou = random.random() < c["hotel"]["chance_aceite"]
        respostas.append({
            "Hotel": c["hotel"]["nome"],
            "Estrelas": "⭐" * c["hotel"]["estrelas"],
            "Distância (km)": c["distancia"],
            "Resposta": "✅ Aceitou" if aceitou else "❌ Recusou",
            "Tempo (s)": random.randint(15, 180),
        })
    aceitos = [r for r in respostas if r["Resposta"].endswith("Aceitou")]
    vencedor = min(aceitos, key=lambda r: r["Tempo (s)"]) if aceitos else None
    return respostas, vencedor


def custo_transporte(km):
    return round(8 + 2.5 * km, 2)  # tarifa base + valor por km


def mensagem_hospede(nome, origem, destino, noites, beneficio, km):
    return (
        f"Olá, {nome}!\n\n"
        f"Pedimos sinceras desculpas: por um problema de disponibilidade, "
        f"não conseguiremos hospedá-lo(a) no {origem} esta noite.\n\n"
        f"Já garantimos sua estadia de {noites} noite(s) no {destino}, "
        f"a {km} km daqui, sem nenhum custo adicional para você. "
        f"Um carro já foi chamado e está a caminho.\n\n"
        f"Como pedido de desculpas, você ganha: {beneficio}.\n\n"
        f"Equipe {origem}"
    )


@st.cache_data
def gerar_historico_reservas():
    """Cria 1 ano de histórico fictício de reservas e no-shows."""
    rng = random.Random(42)
    taxa_base = {0: 0.06, 1: 0.05, 2: 0.05, 3: 0.07, 4: 0.10, 5: 0.12, 6: 0.08}
    historico = []
    hoje = date.today()
    for i in range(365):
        dia = hoje - timedelta(days=i + 1)
        reservas = rng.randint(40, 60)
        no_shows = sum(1 for _ in range(reservas) if rng.random() < taxa_base[dia.weekday()])
        historico.append({"data": dia, "reservas": reservas, "no_shows": no_shows})
    return historico


def taxa_no_show_por_dia(historico):
    reservas = [0] * 7
    no_shows = [0] * 7
    for linha in historico:
        d = linha["data"].weekday()
        reservas[d] += linha["reservas"]
        no_shows[d] += linha["no_shows"]
    return [no_shows[i] / reservas[i] for i in range(7)]


DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


# ------------------------------------------------------------
# 3. TELA
# ------------------------------------------------------------
st.sidebar.title("🏨 Realoca")
nome_origem = st.sidebar.selectbox(
    "Você é a recepção de:", [h["nome"] for h in st.session_state.hoteis]
)
origem = achar_hotel(nome_origem)
st.sidebar.write(f"Categoria: {'⭐' * origem['estrelas']}")
if st.sidebar.button("Reiniciar dados"):
    st.session_state.hoteis = hoteis_iniciais()
    st.session_state.historico = []
    st.session_state.resultado = None
    st.rerun()

st.title("Realoca — realocação de hóspedes em segundos")

aba1, aba2, aba3, aba4 = st.tabs(
    ["🚨 Realocar hóspede", "🏨 Rede de parceiros", "📊 Previsão de no-show", "📜 Histórico"]
)

# ---------- ABA 1: REALOCAR ----------
with aba1:
    col1, col2 = st.columns(2)
    with col1:
        nome_hospede = st.text_input("Nome do hóspede", "Maria Souza")
        tipo = st.selectbox("Tipo de quarto", ["Solteiro", "Casal", "Família"], index=1)
        noites = st.number_input("Noites", min_value=1, max_value=30, value=1)
    with col2:
        raio = st.slider("Raio de busca (km)", 1, 15, 5)
        beneficio = st.text_input("Benefício oferecido", "café da manhã grátis na próxima estadia")

    if st.button("🚨 Disparar pedido de realocação", type="primary"):
        candidatos = buscar_candidatos(origem, tipo, raio)
        if not candidatos:
            st.session_state.resultado = {"erro": True}
        else:
            respostas, vencedor = disparar_pedido(candidatos)
            st.session_state.resultado = {
                "erro": False, "respostas": respostas, "vencedor": vencedor,
                "hospede": nome_hospede, "tipo": tipo, "noites": noites,
                "beneficio": beneficio, "origem": origem["nome"],
            }

    res = st.session_state.resultado
    if res and res["erro"]:
        st.warning("Nenhum parceiro com vaga nesse raio. Tente aumentar o raio de busca.")
    elif res:
        st.subheader("Respostas dos hotéis")
        st.dataframe(res["respostas"], width="stretch", hide_index=True)

        if res["vencedor"] is None:
            st.error("Todos recusaram. Dispare o pedido de novo ou aumente o raio.")
        else:
            v = res["vencedor"]
            destino = achar_hotel(v["Hotel"])
            km = v["Distância (km)"]
            diaria = destino["preco_parceiro"]
            transporte = custo_transporte(km)
            total = diaria * res["noites"] + transporte

            st.success(f"🎉 {v['Hotel']} aceitou em {v['Tempo (s)']} segundos!")
            m1, m2, m3 = st.columns(3)
            m1.metric("Diária combinada", f"R$ {diaria:.2f}")
            m2.metric("Transporte", f"R$ {transporte:.2f}")
            m3.metric("Custo total", f"R$ {total:.2f}")

            st.text_area(
                "Mensagem pronta para o hóspede",
                mensagem_hospede(res["hospede"], res["origem"], v["Hotel"],
                                 res["noites"], res["beneficio"], km),
                height=230,
            )

            if st.button("✅ Confirmar realocação"):
                destino["vagas"][res["tipo"]] -= 1
                st.session_state.historico.append({
                    "Data": date.today().strftime("%d/%m/%Y"),
                    "Hóspede": res["hospede"],
                    "De": res["origem"],
                    "Para": v["Hotel"],
                    "Quarto": res["tipo"],
                    "Noites": res["noites"],
                    "Custo (R$)": total,
                })
                st.session_state.resultado = None
                st.success("Realocação confirmada e registrada no histórico!")

# ---------- ABA 2: PARCEIROS ----------
with aba2:
    tabela = []
    for h in st.session_state.hoteis:
        tabela.append({
            "Hotel": h["nome"],
            "Estrelas": "⭐" * h["estrelas"],
            "Distância de você (km)": round(distancia_km(origem, h), 1),
            "Vagas Solteiro": h["vagas"]["Solteiro"],
            "Vagas Casal": h["vagas"]["Casal"],
            "Vagas Família": h["vagas"]["Família"],
            "Diária parceiro (R$)": h["preco_parceiro"],
        })
    st.dataframe(tabela, width="stretch", hide_index=True)

    st.subheader("Mapa da rede")
    mapa = pd.DataFrame({
        "x (km)": [h["x"] for h in st.session_state.hoteis],
        "y (km)": [h["y"] for h in st.session_state.hoteis],
        "Hotel": [h["nome"] for h in st.session_state.hoteis],
    })
    st.scatter_chart(mapa, x="x (km)", y="y (km)", color="Hotel", height=400)

# ---------- ABA 3: PREVISÃO ----------
with aba3:
    historico = gerar_historico_reservas()
    taxas = taxa_no_show_por_dia(historico)

    st.write("Taxa média de hóspedes que **não aparecem**, por dia da semana (último ano):")
    st.bar_chart(pd.DataFrame({"Taxa de no-show (%)": [t * 100 for t in taxas]}, index=DIAS))

    c1, c2, c3 = st.columns(3)
    data_alvo = c1.date_input("Data", date.today() + timedelta(days=7))
    quartos = c2.number_input("Quartos do hotel", min_value=1, value=50)
    reservas = c3.number_input("Reservas já feitas", min_value=0, value=50)

    taxa = taxas[data_alvo.weekday()]
    esperado = reservas * taxa
    extra_seguro = int(esperado * 0.7)  # margem de segurança: só 70% do esperado

    r1, r2, r3 = st.columns(3)
    r1.metric("Taxa de no-show nesse dia", f"{taxa * 100:.1f}%")
    r2.metric("No-shows esperados", f"{esperado:.1f}")
    r3.metric("Pode vender a mais com segurança", f"{extra_seguro} quarto(s)")

    if reservas >= quartos + extra_seguro:
        st.warning("Atenção: já passou do limite seguro. Pare de vender para essa data.")
    else:
        st.info(f"Ainda dá para vender até {quartos + extra_seguro - reservas} reserva(s).")

# ---------- ABA 4: HISTÓRICO ----------
with aba4:
    if not st.session_state.historico:
        st.write("Nenhuma realocação ainda.")
    else:
        st.dataframe(st.session_state.historico, width="stretch", hide_index=True)
        total = sum(h["Custo (R$)"] for h in st.session_state.historico)
        st.metric("Custo total das realocações", f"R$ {total:.2f}")
