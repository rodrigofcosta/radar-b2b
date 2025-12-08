import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import uuid
import re
import time
import dns.resolver
import base64

# ==============================================================================
# ⚙️ CONFIGURAÇÃO INICIAL
# ==============================================================================
URL_CHAT_N8N = "https://teste.synthix.com.br/webhook-test/radar-b2b" # Seu Webhook

st.set_page_config(
    page_title="Radar B2B | Intelligence", 
    layout="wide", 
    page_icon="fav_ico.png", # Favicon da aba
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 🎨 ESTILO VISUAL (CSS FINAL)
# ==============================================================================

# 1. FUNÇÃO PARA LER IMAGEM (SVG ou PNG) PARA O FUNDO
def get_img_as_base64(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# 2. Configura o fundo da Sidebar
background_image_css = ""
nome_arquivo_fundo = "fundo.svg"  # <--- Tenta carregar fundo.svg (se for PNG, mude aqui)

try:
    bin_str = get_img_as_base64(nome_arquivo_fundo)
    if nome_arquivo_fundo.endswith('.svg'):
        mime_type = "image/svg+xml"
    else:
        mime_type = "image/png"
        
    background_image_css = f"""
        background-image: url("data:{mime_type};base64,{bin_str}");
        background-size: 100% auto;
        background-position: center bottom;
        background-repeat: no-repeat;
    """
except:
    background_image_css = "background-color: #FFFFFF;" # Fallback Branco se não achar arquivo

# 3. INJEÇÃO DO CSS
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    
    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}

    /* --- SIDEBAR --- */
    section[data-testid="stSidebar"] {{
        {background_image_css}
        background-color: #FFFFFF;
        border-right: 1px solid #E0E0E0;
    }}

    /* --- INPUTS DA SIDEBAR (Borda Cinza) --- */
    [data-testid="stSidebar"] [data-testid="stTextInput"] > div > div {{
        border: 1px solid #B0B0B0 !important;
        background-color: #FFFFFF !important;
        border-radius: 6px !important;
    }}
    [data-testid="stSidebar"] [data-testid="stTextInput"] > div > div:focus-within {{
        border-color: #404040 !important;
        box-shadow: 0 0 0 1px #404040 !important;
    }}

    /* --- ALERTA ACESSO RESTRITO (Sem Borda) --- */
    [data-testid="stSidebar"] [data-testid="stAlert"] {{
        background-color: #F0F2F6 !important;
        border: none !important;
        border-radius: 8px !important;
    }}
    [data-testid="stSidebar"] [data-testid="stAlert"] > div {{
        display: flex;
        justify-content: center;
        align-items: center;
        text-align: center;
        width: 100%;
        color: #004B91 !important;
        font-weight: 600;
    }}

    /* --- BOTÕES GERAIS (Sem Borda) --- */
    .stButton button {{
        background-color: #404040 !important; 
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        outline: none !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        font-weight: 600;
        transition: all 0.3s ease;
    }}
    .stButton button:hover {{
        background-color: #000000 !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
    }}
    .stButton button:focus {{
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
    }}

    /* --- CHAT INPUT (Branco Puro) --- */
    .stChatInput {{
        bottom: 40px !important;
        background: transparent !important;
    }}
    [data-testid="stChatInputContainer"] {{
        background-color: transparent !important;
        padding-bottom: 20px;
    }}
    [data-testid="stChatInput"] > div {{
        background-color: #FFFFFF !important;
        border: 1px solid #CCCCCC !important;
        border-radius: 25px !important;
        color: #333333 !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08) !important;
    }}
    [data-testid="stChatInput"] textarea {{
        background-color: #FFFFFF !important;
        color: #333333 !important;
    }}

    /* --- COR DO BOTÃO DE ENVIAR (AZUL) --- */
    [data-testid="stChatInputSubmitButton"] {{
        color: #2D7FFB !important;
    }}
    [data-testid="stChatInputSubmitButton"] svg {{
        width: 20px !important;
        height: 20px !important;
    }}

    /* --- CUSTOMIZAÇÕES GERAIS --- */
    #MainMenu, footer, header {{visibility: hidden;}}
    
    [data-testid="stMetricValue"] {{
        font-size: 2rem !important;
        color: #404040 !important;
    }}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🧠 FUNÇÕES AUXILIARES
# ==============================================================================
def validar_dominio_dns(email):
    try:
        dominio = email.split('@')[1]
        dns.resolver.resolve(dominio, 'MX')
        return True
    except: return False

def validar_dados(email, telefone):
    provedores_proibidos = ['gmail', 'hotmail', 'outlook', 'live', 'yahoo', 'uol', 'bol', 'terra', 'ig', 'icloud']
    if '@' not in email or '.' not in email: return False, "⚠️ E-mail inválido."
    dominio = email.split('@')[-1].split('.')[0].lower()
    if dominio in provedores_proibidos: return False, "⚠️ Utilize e-mail corporativo."
    if not validar_dominio_dns(email): return False, f"⚠️ O domínio @{email.split('@')[1]} parece não existir."
    if telefone:
        tel = re.sub(r'\D', '', telefone)
        if len(tel) != 11: return False, "⚠️ O telefone deve ter DDD + 9 dígitos."
        return True, tel
    return True, None

def consultar_ia(pergunta, session_id, email_user):
    try:
        payload = {"pergunta": pergunta, "sessionId": session_id, "userEmail": email_user}
        response = requests.post(URL_CHAT_N8N, json=payload, timeout=45)
        if response.status_code == 200: return response.json()
        return None
    except: return None

# ==============================================================================
# 🔄 GERENCIAMENTO DE SESSÃO
# ==============================================================================
if "usuario_logado" not in st.session_state: st.session_state.usuario_logado = False
if "session_id" not in st.session_state: st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state: st.session_state.messages = []

# ==============================================================================
# 🧱 BARRA LATERAL
# ==============================================================================
with st.sidebar:
    # 1. LOGO GRANDE
    try:
        c1, c2, c3 = st.columns([0.05, 0.9, 0.05])
        with c2:
            st.image("logo.png", use_container_width=True)
    except:
        st.markdown("## 📡 Radar B2B")

    # 2. TAGLINE
    st.markdown(
        """
        <div style='text-align: center; color: #555; font-size: 14px; margin-top: -10px; margin-bottom: 20px; font-weight: 500; letter-spacing: 0.5px;'>
            O mercado, rua por rua.
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    st.divider()

    if not st.session_state.usuario_logado:
        st.info("🔒 **Acesso Restrito**")
        with st.form("form_login"):
            nome = st.text_input("Nome")
            email = st.text_input("E-mail Corporativo")
            empresa = st.text_input("Empresa")
            telefone = st.text_input("WhatsApp") 
            
            if st.form_submit_button("Acessar Sistema", use_container_width=True):
                if nome and email:
                    valido, msg = validar_dados(email, telefone)
                    if valido:
                        st.session_state.usuario_logado = True
                        st.session_state.email_usuario = email
                        st.session_state.nome_usuario = nome
                        st.rerun()
                    else: st.error(msg)
                else: st.warning("Preencha os campos obrigatórios.")
    else:
        st.success(f"Olá, **{st.session_state.nome_usuario}**")
        st.markdown("### 💡 Dicas de Pesquisa")
        st.markdown("""
        - *Quantas padarias na Tijuca?*
        - *Liste as 5 maiores*
        - *Qual a mais antiga?*
        - *Salões de beleza no Centro*
        """)
        
        if st.button("Sair"):
            st.session_state.usuario_logado = False
            st.session_state.messages = []
            st.rerun()

# ==============================================================================
# 💬 ÁREA DE CHAT E VISUALIZAÇÃO
# ==============================================================================

if len(st.session_state.messages) == 0 and st.session_state.usuario_logado:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #404040;'>Radar B2B</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Encontre seu próximo cliente agora</p>", unsafe_allow_html=True)

# 1. RENDERIZA HISTÓRICO COM AVATARES PERSONALIZADOS
for message in st.session_state.messages:
    # Lógica de Avatar
    if message["role"] == "assistant":
        avatar_icon = "logo.png" # Usa a logo.png
    else:
        avatar_icon = "👤" # Emoji de usuário cinza/neutro
        
    with st.chat_message(message["role"], avatar=avatar_icon):
        st.markdown(message["content"])

if st.session_state.usuario_logado:
    if prompt := st.chat_input("Digite sua pesquisa de mercado..."):
        
        # 2. MOSTRA PERGUNTA DO USUÁRIO
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # 3. MOSTRA RESPOSTA DO BOT (COM LOGO)
        with st.chat_message("assistant", avatar="fav_ico.png"):
            with st.spinner("Analisando dados de mercado..."):
                dados = consultar_ia(prompt, st.session_state.session_id, st.session_state.email_usuario)
                
                if dados:
                    # --- CENÁRIO: BLOQUEIO DE SEGURANÇA (Texto Puro) ---
                    if isinstance(dados, dict) and "mensagem_bloqueio" in dados:
                        msg = dados["mensagem_bloqueio"]
                        st.error(f"⛔ **{msg}**")
                        st.session_state.messages.append({"role": "assistant", "content": f"⛔ **{msg}**"})
                    
                    else:
                        # --- CENÁRIO: DADOS VÁLIDOS ---
                        registros = []
                        if isinstance(dados, dict) and "data" in dados: registros = dados["data"]
                        elif isinstance(dados, list): registros = dados
                        else: registros = [dados]

                        if len(registros) == 0:
                            st.warning("Nenhum registro encontrado.")
                        else:
                            df = pd.DataFrame(registros)
                            
                            # A) CONTAGEM SIMPLES
                            if 'total' in df.columns and len(df) == 1 and 'Local' not in df.columns:
                                v = df.iloc[0]['total']
                                st.metric("Total Encontrado", v)
                                st.session_state.messages.append({"role": "assistant", "content": f"**Total:** {v}"})
                            
                            # B) DISTRIBUIÇÃO (Gráfico por Bairro/Rua) - ESCALA DE CINZA
                            elif 'Local' in df.columns:
                                total = df['Total'].sum()
                                st.metric("Total Geral", total)
                                
                                # Gráfico em Tons de Cinza
                                fig = px.bar(
                                    df.head(15), x="Local", y="Total", 
                                    text_auto=True, template="plotly_white",
                                    color="Total",
                                    color_continuous_scale=["#E0E0E0", "#404040"] # Gradiente Cinza
                                )
                                fig.update_traces(textfont_color="black")
                                fig.update_layout(coloraxis_showscale=False)
                                
                                st.plotly_chart(fig, use_container_width=True)
                                st.dataframe(df, use_container_width=True, hide_index=True)
                                st.session_state.messages.append({"role": "assistant", "content": f"Encontrei {total} registros."})
                            
                            # C) LISTA / RANKING / TABELA COMPLETA
                            else:
                                cols = ["Nome", "Endereço", "Telefone"]
                                prompt_lower = prompt.lower()
                                tem_capital = any(x in prompt_lower for x in ["maior", "menor", "ranking", "capital"])
                                tem_tempo = any(x in prompt_lower for x in ["antig", "nov", "recent", "data", "abriu"])
                                
                                txt_resp = f"✅ **Encontrei {len(df)} registros.**"
                                st.markdown(txt_resp)

                                # --- VISUALIZAÇÃO: CAPITAL SOCIAL (GRÁFICO CINZA) ---
                                if tem_capital and "Capital Social" in df.columns:
                                    cols.append("Capital Social")
                                    df["Capital_Num"] = pd.to_numeric(df["Capital Social"], errors='coerce').fillna(0)
                                    df_top = df.nlargest(15, "Capital_Num")
                                    df_top["Legenda"] = df_top["Nome"] + " (" + df_top["Endereço"].apply(lambda x: x.split(',')[0] if ',' in x else x) + ")"
                                    
                                    st.markdown("### 🏆 Ranking Financeiro")
                                    fig = px.bar(
                                        df_top, x="Legenda", y="Capital_Num", 
                                        template="plotly_white", text_auto='.2s',
                                        color="Capital_Num",
                                        color_continuous_scale=["#E0E0E0", "#404040"] # Gradiente Cinza
                                    )
                                    fig.update_traces(textfont_color="black", textfont_size=12, cliponaxis=False)
                                    fig.update_layout(xaxis_title=None, yaxis_title=None, coloraxis_showscale=False, height=400)
                                    fig.update_xaxes(showgrid=False)
                                    
                                    st.plotly_chart(fig, use_container_width=True)
                                    df["Capital Social"] = df["Capital_Num"]

                                # --- VISUALIZAÇÃO: TEMPO ---
                                elif tem_tempo and "Início" in df.columns:
                                    cols.append("Início")

                                # --- TABELA PREMIUM INTERATIVA ---
                                final_cols = [c for c in cols if c in df.columns]
                                
                                col_config = {
                                    "Capital Social": st.column_config.NumberColumn(
                                        "Capital Social", format="R$ %.2f", help="Capital Social registrado"
                                    ),
                                    "Início": st.column_config.DateColumn(
                                        "Abertura", format="DD/MM/YYYY"
                                    ),
                                    "Telefone": st.column_config.TextColumn(
                                        "Contato", help="Telefone Principal"
                                    )
                                }

                                st.dataframe(
                                    df[final_cols], 
                                    use_container_width=True, 
                                    hide_index=True, 
                                    height=500,
                                    column_config=col_config
                                )
                                st.session_state.messages.append({"role": "assistant", "content": txt_resp})
                else:
                    st.error("Erro de comunicação com o servidor.")
else:
    st.chat_input("Faça login na barra lateral para pesquisar...", disabled=True)