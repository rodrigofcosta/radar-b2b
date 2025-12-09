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
# ⚙️ CONFIGURAÇÃO DE URLS (PRODUÇÃO)
# ==============================================================================
# 1. URL DO CHAT (Mude aqui para sua URL de Produção do n8n)
URL_CHAT_N8N = "https://prd.synthix.com.br/webhook/radar-b2b" 

# 2. URL DE CAPTURA DE LEADS (Cadastro de usuário)
URL_LEAD_N8N = "https://prd.synthix.com.br/webhook/cadastrar-lead"

st.set_page_config(
    page_title="Radar B2B | Intelligence", 
    layout="wide", 
    page_icon="fav_ico.png",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 🎨 ESTILO VISUAL (CSS FINAL)
# ==============================================================================
# ... (MANTENHA O BLOCO DE CSS IGUAL AO ANTERIOR - SEM ALTERAÇÕES) ...
# Para economizar espaço aqui, vou pular o CSS pois ele não muda. 
# Se for copiar e colar tudo, pegue o bloco CSS da resposta anterior e cole aqui.
# ==============================================================================

def get_img_as_base64(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

background_image_css = ""
nome_arquivo_fundo = "fundo.svg"

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
    background_image_css = "background-color: #FFFFFF;"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    section[data-testid="stSidebar"] {{ {background_image_css} background-color: #FFFFFF; border-right: 1px solid #E0E0E0; }}
    [data-testid="stSidebar"] [data-testid="stTextInput"] > div > div {{ border: 1px solid #B0B0B0 !important; background-color: #FFFFFF !important; border-radius: 6px !important; }}
    [data-testid="stSidebar"] [data-testid="stTextInput"] > div > div:focus-within {{ border-color: #404040 !important; box-shadow: 0 0 0 1px #404040 !important; }}
    [data-testid="stSidebar"] [data-testid="stAlert"] {{ background-color: #F0F2F6 !important; border: none !important; border-radius: 8px !important; }}
    [data-testid="stSidebar"] [data-testid="stAlert"] > div {{ display: flex; justify-content: center; align-items: center; text-align: center; width: 100%; color: #004B91 !important; font-weight: 600; }}
    .stButton button {{ background-color: #404040 !important; color: white !important; border-radius: 8px !important; border: none !important; outline: none !important; box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important; font-weight: 600; transition: all 0.3s ease; }}
    .stButton button:hover {{ background-color: #000000 !important; box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important; }}
    .stChatInput {{ bottom: 40px !important; background: transparent !important; }}
    [data-testid="stChatInputContainer"] {{ background-color: transparent !important; padding-bottom: 20px; }}
    [data-testid="stChatInput"] > div {{ background-color: #FFFFFF !important; border: 1px solid #CCCCCC !important; border-radius: 25px !important; color: #333333 !important; box-shadow: 0 4px 15px rgba(0,0,0,0.08) !important; }}
    [data-testid="stChatInput"] textarea {{ background-color: #FFFFFF !important; color: #333333 !important; }}
    [data-testid="stChatInputSubmitButton"] {{ color: #2D7FFB !important; }}
    [data-testid="stChatInputSubmitButton"] svg {{ width: 20px !important; height: 20px !important; }}
    #MainMenu, footer, header {{visibility: hidden;}}
    [data-testid="stMetricValue"] {{ font-size: 2rem !important; color: #404040 !important; }}
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

# --- NOVA FUNÇÃO: SALVAR LEAD ---
def salvar_lead(nome, email, empresa, telefone):
    """Envia os dados do usuário para o n8n ao fazer login"""
    try:
        if URL_LEAD_N8N:
            payload = {
                "nome": nome,
                "email": email,
                "empresa": empresa,
                "cargo": cargo,
                "telefone": telefone,
                "data_acesso": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            # Envia em background (timeout curto para não travar o app)
            requests.post(URL_LEAD_N8N, json=payload, timeout=2)
    except:
        # Se falhar o webhook, não impede o usuário de logar (silencioso)
        pass

def consultar_ia(pergunta, session_id, email_user):
    try:
        payload = {"pergunta": pergunta, "sessionId": session_id, "userEmail": email_user}
        response = requests.post(URL_CHAT_N8N, json=payload, timeout=45)
        if response.status_code == 200: return response.json()
        return None
    except: return None

# ==============================================================================
# 🔄 SESSÃO
# ==============================================================================
if "usuario_logado" not in st.session_state: st.session_state.usuario_logado = False
if "session_id" not in st.session_state: st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state: st.session_state.messages = []

# ==============================================================================
# 🧱 BARRA LATERAL (COM AVISO DE COBERTURA RJ)
# ==============================================================================
with st.sidebar:
    # 1. LOGO GRANDE
    try:
        c1, c2, c3 = st.columns([0.05, 0.9, 0.05])
        with c2: st.image("logo.png", use_container_width=True)
    except: st.markdown("## 📡 Radar B2B")

    # 2. TAGLINE
    st.markdown("""<div style='text-align: center; color: #555; font-size: 14px; margin-top: -10px; margin-bottom: 20px; font-weight: 500; letter-spacing: 0.5px;'>O mercado, rua por rua.</div>""", unsafe_allow_html=True)
    st.divider()

    if not st.session_state.usuario_logado:
        # --- LOGIN (SEM ALTERAÇÕES) ---
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
                        # Disparo do Webhook
                        tel_limpo = msg if telefone else ""
                        salvar_lead(nome, email, empresa, tel_limpo)
                        
                        st.session_state.usuario_logado = True
                        st.session_state.email_usuario = email
                        st.session_state.nome_usuario = nome
                        st.rerun()
                    else: st.error(msg)
                else: st.warning("Preencha os campos obrigatórios.")
    else:
        # --- ÁREA LOGADA ---
        st.success(f"Olá, **{st.session_state.nome_usuario}**")
        
        st.markdown("### 💡 Dicas de Pesquisa")
        st.markdown("""
        - *Quantas padarias na Tijuca?*
        - *Liste as 5 maiores*
        - *Qual a mais antiga?*
        - *Salões de beleza no Centro*
        """)
        
        st.markdown("---")
        
        # --- GUIA & INSTRUÇÕES (ATUALIZADO COM RJ) ---
        with st.expander("ℹ️ Guia & Cobertura", expanded=False):
            st.markdown("""
            **🗺️ Cobertura Geográfica**
            O banco de dados contempla exclusivamente empresas do **Estado do Rio de Janeiro (RJ)**.
            
            **📍 Localização Precisa**
            Sempre cite o **Município**, **Bairro** ou a **Rua** para filtrar melhor os resultados.
            
            **📚 Busca por Atividade**
            O sistema busca pelo código oficial (CNAE). Se não encontrar pelo nome comum, tente um sinônimo.
            
            **🤝 Colabore**
            Não achou um nicho específico?
            [**Me avise no LinkedIn**](https://www.linkedin.com/in/rodrigo-f-costa/) para eu adicionar ao dicionário!
            
            <div style='font-size: 11px; color: #888; margin-top: 10px; border-top: 1px solid #eee; padding-top: 5px;'>
            Fonte: Dados Públicos da Receita Federal do Brasil.
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Sair"):
            st.session_state.usuario_logado = False
            st.session_state.messages = []
            st.rerun()

# ==============================================================================
# 💬 CHAT
# ==============================================================================
if len(st.session_state.messages) == 0 and st.session_state.usuario_logado:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #404040;'>Radar B2B</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Encontre seu próximo cliente agora</p>", unsafe_allow_html=True)

for message in st.session_state.messages:
    icon = "fav_ico.png" if message["role"] == "assistant" else "👤"
    with st.chat_message(message["role"], avatar=icon):
        st.markdown(message["content"])

if st.session_state.usuario_logado:
    if prompt := st.chat_input("Digite sua pesquisa de mercado..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"): st.markdown(prompt)

        with st.chat_message("assistant", avatar="fav_ico.png"):
            with st.spinner("Analisando dados de mercado..."):
                dados = consultar_ia(prompt, st.session_state.session_id, st.session_state.email_usuario)
                
                if dados:
                    if isinstance(dados, dict) and "mensagem_bloqueio" in dados:
                        msg = dados["mensagem_bloqueio"]
                        st.error(f"⛔ **{msg}**")
                        st.session_state.messages.append({"role": "assistant", "content": f"⛔ **{msg}**"})
                    else:
                        registros = []
                        if isinstance(dados, dict) and "data" in dados: registros = dados["data"]
                        elif isinstance(dados, list): registros = dados
                        else: registros = [dados]

                        if len(registros) == 0: st.warning("Nenhum registro encontrado.")
                        else:
                            df = pd.DataFrame(registros)
                            
                            if 'total' in df.columns and len(df) == 1 and 'Local' not in df.columns:
                                v = df.iloc[0]['total']
                                st.metric("Total Encontrado", v)
                                st.session_state.messages.append({"role": "assistant", "content": f"**Total:** {v}"})
                            
                            elif 'Local' in df.columns:
                                total = df['Total'].sum()
                                st.metric("Total Geral", total)
                                fig = px.bar(df.head(15), x="Local", y="Total", text_auto=True, template="plotly_white", color="Total", color_continuous_scale=["#E0E0E0", "#404040"])
                                fig.update_traces(textfont_color="black")
                                fig.update_layout(coloraxis_showscale=False)
                                st.plotly_chart(fig, use_container_width=True)
                                st.dataframe(df, use_container_width=True, hide_index=True)
                                st.session_state.messages.append({"role": "assistant", "content": f"Encontrei {total} registros."})
                            
                            else:
                                cols = ["Nome", "Endereço", "Telefone"]
                                prompt_lower = prompt.lower()
                                tem_capital = any(x in prompt_lower for x in ["maior", "menor", "ranking", "capital"])
                                tem_tempo = any(x in prompt_lower for x in ["antig", "nov", "recent", "data", "abriu"])
                                txt_resp = f"✅ **Encontrei {len(df)} registros.**"
                                st.markdown(txt_resp)

                                if tem_capital and "Capital Social" in df.columns:
                                    cols.append("Capital Social")
                                    df["Capital_Num"] = pd.to_numeric(df["Capital Social"], errors='coerce').fillna(0)
                                    df_top = df.nlargest(15, "Capital_Num")
                                    df_top["Legenda"] = df_top["Nome"] + " (" + df_top["Endereço"].apply(lambda x: x.split(',')[0] if ',' in x else x) + ")"
                                    st.markdown("### 🏆 Ranking Financeiro")
                                    fig = px.bar(df_top, x="Legenda", y="Capital_Num", template="plotly_white", text_auto='.2s', color="Capital_Num", color_continuous_scale=["#E0E0E0", "#404040"])
                                    fig.update_traces(textfont_color="black", textfont_size=12, cliponaxis=False)
                                    fig.update_layout(xaxis_title=None, yaxis_title=None, coloraxis_showscale=False, height=400)
                                    fig.update_xaxes(showgrid=False)
                                    st.plotly_chart(fig, use_container_width=True)
                                    df["Capital Social"] = df["Capital_Num"]
                                elif tem_tempo and "Início" in df.columns: cols.append("Início")

                                final_cols = [c for c in cols if c in df.columns]
                                col_config = {
                                    "Capital Social": st.column_config.NumberColumn("Capital Social", format="R$ %.2f"),
                                    "Início": st.column_config.DateColumn("Abertura", format="DD/MM/YYYY"),
                                    "Telefone": st.column_config.TextColumn("Contato")
                                }
                                st.dataframe(df[final_cols], use_container_width=True, hide_index=True, height=500, column_config=col_config)
                                st.session_state.messages.append({"role": "assistant", "content": txt_resp})
                else: st.error("Erro de comunicação com o servidor.")
else: st.chat_input("Faça login na barra lateral para pesquisar...", disabled=True)



