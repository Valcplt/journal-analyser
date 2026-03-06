import streamlit as st
import anthropic
import base64
import json
import re
from PIL import Image
import io

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Analyseur de Journal Intime & Performance",
    page_icon="📔",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* ── Header ── */
  .main-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    padding: 2.5rem 2rem;
    border-radius: 16px;
    margin-bottom: 2rem;
    text-align: center;
    box-shadow: 0 8px 32px rgba(0,0,0,.3);
  }
  .main-header h1 {
    color: #e2e8f0;
    font-size: 2.2rem;
    font-weight: 700;
    margin: 0 0 .5rem;
    letter-spacing: -.5px;
  }
  .main-header p { color: #94a3b8; font-size: 1rem; margin: 0; }

  /* ── Cards ── */
  .card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 4px 16px rgba(0,0,0,.2);
  }
  .card-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: .5rem;
  }

  /* ── Score bars ── */
  .score-row { margin-bottom: .9rem; }
  .score-label {
    display: flex;
    justify-content: space-between;
    color: #cbd5e1;
    font-size: .88rem;
    margin-bottom: .35rem;
  }
  .bar-track {
    background: #0f172a;
    border-radius: 99px;
    height: 10px;
    overflow: hidden;
  }
  .bar-fill {
    height: 100%;
    border-radius: 99px;
    transition: width .6s ease;
  }
  .bar-positive { background: linear-gradient(90deg,#22c55e,#4ade80); }
  .bar-negative { background: linear-gradient(90deg,#ef4444,#f87171); }
  .bar-neutral  { background: linear-gradient(90deg,#3b82f6,#60a5fa); }

  /* ── Badges ── */
  .badge {
    display: inline-block;
    padding: .2rem .7rem;
    border-radius: 99px;
    font-size: .78rem;
    font-weight: 600;
    margin-right: .4rem;
  }
  .badge-pos { background:#14532d; color:#86efac; }
  .badge-neg { background:#7f1d1d; color:#fca5a5; }
  .badge-neu { background:#1e3a5f; color:#93c5fd; }

  /* ── Transcription box ── */
  .transcription-box {
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 1.2rem 1.4rem;
    color: #cbd5e1;
    font-size: .93rem;
    line-height: 1.7;
    white-space: pre-wrap;
    font-family: 'Georgia', serif;
  }

  /* ── Conclusion ── */
  .conclusion-box {
    background: linear-gradient(135deg,#0f3460,#1a1a2e);
    border: 1px solid #3b82f6;
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    color: #e2e8f0;
    font-size: .97rem;
    line-height: 1.8;
  }

  /* ── Quote ── */
  .quote {
    border-left: 3px solid #3b82f6;
    margin: .6rem 0;
    padding: .3rem .8rem;
    color: #94a3b8;
    font-style: italic;
    font-size: .88rem;
  }

  /* ── Upload zone ── */
  .upload-hint {
    text-align: center;
    color: #64748b;
    font-size: .85rem;
    margin-top: .5rem;
  }

  /* ── Sidebar ── */
  .sidebar-info {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 1rem;
    font-size: .83rem;
    color: #94a3b8;
    line-height: 1.6;
  }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    api_key = st.text_input(
        "Clé API Anthropic",
        type="password",
        placeholder="sk-ant-...",
        help="Votre clé API Anthropic (jamais stockée)",
    )
    st.markdown("---")
    st.markdown("""
<div class="sidebar-info">
<b>📖 Comment ça marche ?</b><br><br>
1. Collez votre clé API ci-dessus<br>
2. Uploadez une photo de votre carnet<br>
3. Cliquez sur <b>Lancer l'Analyse</b><br>
4. Consultez votre tableau de bord<br><br>
<b>Modèle :</b> Claude 3.5 Sonnet (Vision)<br>
<b>Formats :</b> JPG, PNG, JPEG
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>📔 Analyseur de Journal Intime & Performance</h1>
  <p>Transcription intelligente · Analyse sémantique · Tableau de bord émotionnel</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  SYSTEM PROMPT
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es un expert en analyse sémantique et en psychologie positive.
Tu vas analyser une image d'un carnet de notes manuscrit et retourner UNIQUEMENT un objet JSON valide, sans aucun texte autour.

Structure JSON exacte à respecter :
{
  "transcription": "texte transcrit complet, avec [?] pour les mots illisibles",
  "vie_personnelle": {
    "extraits": ["phrase ou segment 1", "phrase ou segment 2"],
    "positivite": 0,
    "negativite": 0,
    "neutralite": 0,
    "justification_pos": "explication avec citations",
    "justification_neg": "explication avec citations",
    "justification_neu": "explication avec citations"
  },
  "entrainement_sportif": {
    "extraits": ["phrase ou segment 1", "phrase ou segment 2"],
    "positivite": 0,
    "negativite": 0,
    "neutralite": 0,
    "justification_pos": "explication avec citations",
    "justification_neg": "explication avec citations",
    "justification_neu": "explication avec citations"
  },
  "conclusion": "analyse globale de l'état d'esprit, tendances positives/négatives, nuances importantes"
}

Règles strictes :
1. TRANSCRIPTION : Transcris fidèlement sans jamais deviner les mots illisibles (utilise [?]).
2. SEGMENTATION : Sépare ce qui relève de la 'Vie Personnelle' et de 'l'Entraînement Sportif'. Si une catégorie est absente, ses scores sont 0 et extraits est [].
3. ANALYSE : Les scores positivite + negativite + neutralite doivent totaliser exactement 100 pour chaque catégorie présente.
4. NUANCE : La neutralité ne doit pas être jugée négativement, mais les nuances de rédaction des faits neutres influencent le score global.
5. JUSTIFICATION : Cite des extraits entre guillemets pour expliquer chaque score.
6. Retourne UNIQUEMENT le JSON, rien d'autre."""

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def image_to_base64(uploaded_file) -> tuple[str, str]:
    """Convert uploaded file to base64 string and detect media type."""
    ext = uploaded_file.name.split(".")[-1].lower()
    media_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}
    media_type = media_map.get(ext, "image/jpeg")
    data = base64.standard_b64encode(uploaded_file.read()).decode("utf-8")
    return data, media_type


def analyse_image(api_key: str, img_b64: str, media_type: str) -> dict:
    """Call Claude vision API and return parsed JSON."""
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": img_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Analyse ce carnet de notes manuscrit et retourne le JSON demandé.",
                    },
                ],
            }
        ],
    )
    raw = message.content[0].text.strip()
    # Strip possible markdown fences
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def score_bar(label: str, value: int, css_class: str):
    """Render a custom HTML progress bar."""
    st.markdown(f"""
<div class="score-row">
  <div class="score-label"><span>{label}</span><span><b>{value}%</b></span></div>
  <div class="bar-track">
    <div class="bar-fill {css_class}" style="width:{value}%"></div>
  </div>
</div>
""", unsafe_allow_html=True)


def render_category(title: str, icon: str, data: dict):
    """Render a full category card."""
    extraits = data.get("extraits", [])
    pos = data.get("positivite", 0)
    neg = data.get("negativite", 0)
    neu = data.get("neutralite", 0)

    with st.container():
        st.markdown(f'<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<div class="card-title">{icon} {title}</div>', unsafe_allow_html=True)

        if not extraits:
            st.markdown('<p style="color:#64748b;font-size:.9rem;">Aucun contenu détecté dans cette catégorie.</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            return

        # Scores
        score_bar("😊 Positivité", pos, "bar-positive")
        score_bar("😔 Négativité", neg, "bar-negative")
        score_bar("😐 Neutralité", neu, "bar-neutral")

        st.markdown("---")

        # Extraits
        st.markdown('<div style="color:#94a3b8;font-size:.88rem;margin-bottom:.4rem;font-weight:600;">📝 Extraits identifiés</div>', unsafe_allow_html=True)
        for e in extraits:
            st.markdown(f'<div class="quote">{e}</div>', unsafe_allow_html=True)

        st.markdown("---")

        # Justifications
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<span class="badge badge-pos">✅ Positif</span>', unsafe_allow_html=True)
            st.markdown(f'<p style="color:#86efac;font-size:.83rem;margin-top:.4rem;">{data.get("justification_pos","—")}</p>', unsafe_allow_html=True)
        with col2:
            st.markdown('<span class="badge badge-neg">⚠️ Négatif</span>', unsafe_allow_html=True)
            st.markdown(f'<p style="color:#fca5a5;font-size:.83rem;margin-top:.4rem;">{data.get("justification_neg","—")}</p>', unsafe_allow_html=True)
        with col3:
            st.markdown('<span class="badge badge-neu">🔵 Neutre</span>', unsafe_allow_html=True)
            st.markdown(f'<p style="color:#93c5fd;font-size:.83rem;margin-top:.4rem;">{data.get("justification_neu","—")}</p>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  MAIN UI
# ─────────────────────────────────────────────
col_upload, col_preview = st.columns([1.2, 1])

with col_upload:
    st.markdown("### 📁 Importer une page de carnet")
    uploaded = st.file_uploader(
        "Glissez votre image ici ou cliquez pour parcourir",
        type=["jpg", "jpeg", "png"],
        label_visibility="collapsed",
    )
    st.markdown('<p class="upload-hint">Formats acceptés : JPG · JPEG · PNG · Taille max : 5 Mo</p>', unsafe_allow_html=True)

with col_preview:
    if uploaded:
        img = Image.open(uploaded)
        st.image(img, caption="Aperçu de votre carnet", use_container_width=True)
    else:
        st.markdown("""
<div style="height:200px;background:#1e293b;border:2px dashed #334155;
     border-radius:12px;display:flex;align-items:center;justify-content:center;">
  <span style="color:#475569;font-size:.9rem;">Aperçu de l'image</span>
</div>""", unsafe_allow_html=True)

st.markdown("---")

# ── Analyse button ──
btn_col, _ = st.columns([1, 3])
with btn_col:
    analyse_btn = st.button("🚀 Lancer l'Analyse", use_container_width=True, type="primary")

# ─────────────────────────────────────────────
#  ANALYSIS FLOW
# ─────────────────────────────────────────────
if analyse_btn:
    if not api_key:
        st.error("⚠️ Veuillez saisir votre clé API Anthropic dans la barre latérale.")
    elif not uploaded:
        st.warning("⚠️ Veuillez uploader une image avant de lancer l'analyse.")
    else:
        with st.spinner("🔍 Analyse en cours… transcription et interprétation sémantique…"):
            try:
                uploaded.seek(0)
                img_b64, media_type = image_to_base64(uploaded)
                result = analyse_image(api_key, img_b64, media_type)
                st.session_state["result"] = result
                st.success("✅ Analyse terminée avec succès !")
            except json.JSONDecodeError:
                st.error("❌ Le modèle n'a pas retourné un JSON valide. Réessayez.")
            except anthropic.AuthenticationError:
                st.error("❌ Clé API invalide. Vérifiez votre clé Anthropic.")
            except Exception as e:
                st.error(f"❌ Erreur inattendue : {e}")

# ─────────────────────────────────────────────
#  RESULTS DASHBOARD
# ─────────────────────────────────────────────
if "result" in st.session_state:
    r = st.session_state["result"]
    st.markdown("## 📊 Tableau de Bord")

    # ── Transcription ──
    with st.expander("📄 Transcription complète", expanded=True):
        st.markdown(f'<div class="transcription-box">{r.get("transcription","Aucune transcription disponible.")}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("## 🧠 Analyse par Catégorie")

    col_perso, col_sport = st.columns(2)
    with col_perso:
        render_category("Vie Personnelle", "🌱", r.get("vie_personnelle", {}))
    with col_sport:
        render_category("Entraînement Sportif", "🏋️", r.get("entrainement_sportif", {}))

    st.markdown("---")

    # ── Global scores ──
    st.markdown("### 📈 Scores Globaux")
    vp = r.get("vie_personnelle", {})
    es = r.get("entrainement_sportif", {})

    def avg_score(key):
        vals = [v for v in [vp.get(key, 0), es.get(key, 0)] if v > 0]
        return round(sum(vals) / len(vals)) if vals else 0

    g_col1, g_col2, g_col3 = st.columns(3)
    with g_col1:
        st.metric("😊 Positivité globale", f"{avg_score('positivite')}%")
    with g_col2:
        st.metric("😔 Négativité globale", f"{avg_score('negativite')}%")
    with g_col3:
        st.metric("😐 Neutralité globale", f"{avg_score('neutralite')}%")

    st.markdown("---")

    # ── Conclusion ──
    st.markdown("### 💡 Conclusion & État d'Esprit Global")
    conclusion = r.get("conclusion", "Aucune conclusion disponible.")
    st.markdown(f'<div class="conclusion-box">🧭 {conclusion}</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Réinitialiser l'analyse"):
        del st.session_state["result"]
        st.rerun()
