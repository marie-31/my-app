import pandas as pd
import streamlit as st
import altair as alt

from altair import datum
from typing import Tuple

URL_OPENCOVID19 = "https://raw.githubusercontent.com/opencovid19-fr/data/master/dist/chiffres-cles.csv"


# make title
st.title("DataViz App Covid-19 🦠")


@st.cache
def get_data(url: str = URL_OPENCOVID19) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    1 - Get data from opencovid19 repository
    2 - Transform raw data into dataframe
    3 - Returns df_covid19_fr (columns = ['date', 'type', 'nombre']) and
                df_covid19_region (columns = ['date', 'maille_nom', 'cas_confirmes', 'deces', 'delta_deces',
                                              'delta_cas_confirmes', 'fatality_rate', 'days_after_5_deaths',
                                               'days_after_50_confirmed']) 
    """
    # 1 - Get data
    data = pd.read_csv(url)

    # 2 - Make some transformations to obtain df_covid19_fr (columns = ['date', 'type', 'nombre'])
    df_covid19_fr = data[
        (data.granularite == "pays") & (data.source_type == "sante-publique-france")
    ]
    # reshape df
    df_covid19_fr = pd.melt(
        df_covid19_fr,
        id_vars=["date"],
        value_vars=["cas_confirmes", "deces", "reanimation"],
        var_name="type",
        value_name="nombre",
    )
    df_covid19_fr = df_covid19_fr.fillna(value=0)

    # 2 - Make some transformation to obtain df_covid19_region
    df_covid19_region = data[
        (data.granularite == "region")
        & (data.source_type == "agences-regionales-sante")
    ]
    df_covid19_region = df_covid19_region[
        ["date", "maille_nom", "cas_confirmes", "deces"]
    ]
    df_covid19_region = df_covid19_region.sort_values(by=["maille_nom", "date"])
    # compute delta_deces by making the diff between rows on deces grouped by region
    df_covid19_region["delta_deces"] = df_covid19_region.groupby("maille_nom")[
        "deces"
    ].diff()
    # compute delta_cas_confirmes by making the diff between rows on cas_confirmes grouped by region
    df_covid19_region["delta_cas_confirmes"] = df_covid19_region.groupby("maille_nom")[
        "cas_confirmes"
    ].diff()
    # compute fatality rate
    df_covid19_region["fatality_rate"] = (
        df_covid19_region["deces"] / df_covid19_region["cas_confirmes"]
    )
    # create a new index based from day after 5 deaths
    df_covid19_region["days_after_5_deaths"] = (
        df_covid19_region[df_covid19_region.deces > 5]
        .groupby("maille_nom")["deces"]
        .rank(method="first", ascending=True)
    )
    # create a new index based from day after 50 confirmed
    df_covid19_region["days_after_50_confirmed"] = (
        df_covid19_region[df_covid19_region.cas_confirmes > 50]
        .groupby("maille_nom")["cas_confirmes"]
        .rank(method="first", ascending=True)
    )
    df_covid19_region.reset_index(drop=True)

    return df_covid19_region, df_covid19_fr


# get data
df_covid19_region, df_covid19_fr = get_data()

# create streamlit sidebar
regions = list(df_covid19_region.maille_nom.unique())
option = st.sidebar.selectbox("Visualisation: ", ("graph", "heatmap", "histo"))
check_box_table = st.sidebar.checkbox("Afficher les données")
check_box_analyse = st.sidebar.checkbox("Afficher l'analyse")

multiselection = st.sidebar.multiselect(
    "Selection des régions:", regions, default=regions
)
st.sidebar.info(
    "Merci à tous contributeurs du projet [opencovid19-fr](https://github.com/opencovid19-fr/data) pour leur travail de collecte des données officielles sur la progression de l'épidémie en France."
)

# get df_covid19_region based on region in multiselection
df_covid19_region = df_covid19_region[
    df_covid19_region["maille_nom"].isin(multiselection)
].sort_values(by=["maille_nom", "date"], ascending=[True, False])


if check_box_table:
    st.write(df_covid19_region)

if option == "graph":
    if st.checkbox("Log Scale"):
        scale = alt.Scale(type="log", domain=[10, 5000], clamp=True)
    else:
        scale = alt.Scale(type="linear")

    if check_box_analyse:
        st.info(
            "[03/22] Les régions Grand-Est, Ile-de-France et Haut-de-France sont les plus touchées par l'épidémie. "
            "Par ailleurs l'affiche en échelle Log, nous montre que l'ensemble des régions suivent la même croissance en terme d'évolution"
        )
    # make plot on nb of deces by regions
    c_deces = (
        alt.Chart(df_covid19_region)
        .mark_line(point=True)
        .encode(
            alt.X("days_after_5_deaths"),
            alt.Y("deces", scale=scale),
            alt.Color("maille_nom"),
            tooltip=["days_after_5_deaths", "deces", "maille_nom"],
        )
        .interactive()
    )

    # make plot on nb confirmed by regions
    c_confirmed = (
        alt.Chart(df_covid19_region)
        .mark_line(point=True)
        .encode(
            alt.X("days_after_50_confirmed"),
            alt.Y("cas_confirmes", scale=scale),
            alt.Color("maille_nom"),
            tooltip=["days_after_5_deaths", "deces", "maille_nom"],
        )
        .interactive()
    )

    st.altair_chart(c_deces, use_container_width=True)
    st.altair_chart(c_confirmed, use_container_width=True)

elif option == "heatmap":
    if check_box_analyse:
        st.info(
            "[03/22] Les régions Grand-Est, Ile-de-France et Haut-de-France ont été les premières touchées par l'épidémie. "
        )

    # make heatmap on nb of deces by regions
    c_heatmap_deces = (
        alt.Chart(df_covid19_region)
        .mark_rect()
        .encode(
            alt.X("date"),
            alt.Y("maille_nom:N"),
            alt.Color("delta_deces:Q", scale=alt.Scale(scheme="lightmulti")),
            tooltip=["date", "maille_nom", "delta_deces"],
        )
        .interactive()
    )

    # make heatmap on nb of confirmed by regions
    c_heatmap_confirmed = (
        alt.Chart(df_covid19_region)
        .mark_rect()
        .encode(
            alt.X("date"),
            alt.Y("maille_nom:N"),
            alt.Color("delta_cas_confirmes:Q", scale=alt.Scale(scheme="lightmulti")),
            tooltip=["date", "maille_nom", "delta_deces"],
        )
        .transform_filter((datum.delta_cas_confirmes >= 0))
        .interactive()
    )
    c_circle_evo = (
        alt.Chart(df_covid19_region)
        .mark_circle()
        .encode(
            alt.X("date"),
            alt.Y("maille_nom:N"),
            alt.Color("deces:Q", scale=alt.Scale(scheme="lightmulti")),
            alt.Size("cas_confirmes:N", bin=alt.Bin(maxbins=5)),
        )
    )

    st.altair_chart(c_heatmap_deces, use_container_width=True)
    st.altair_chart(c_heatmap_confirmed, use_container_width=True)
    st.altair_chart(c_circle_evo, use_container_width=True)


elif option == "histo":

    # make histo on evo in france
    c_evo_fr = (
        alt.Chart(df_covid19_fr)
        .mark_bar()
        .encode(x="date", y=alt.Y("nombre"), color="type")
        .transform_filter((datum.date >= "2020-03-01"))
    )
    # make histo on fatality rate in france
    c_histo_fatality_rate = (
        alt.Chart(df_covid19_region)
        .mark_bar()
        .encode(alt.Y("maille_nom:N", sort="-x"), alt.X("mean(fatality_rate):Q"),)
        .transform_filter((datum.date >= "2020-03-10"))
    )

    if check_box_analyse:
        st.info(
            "[03/22] Evolution par jour du nombre de cas, de réanimation et de décès. Chaque jour, les valeurs augmentent."
        )

    st.altair_chart(c_evo_fr, use_container_width=True)

    if check_box_analyse:
        st.info(
            "[03/22] Le graphique ci-dessous estime le taux de mortalité de l'épidémie Covid-19 dans les différentes régions de France. "
            "⚠️ A  noter que cette valeur dépend du nombre de test et par conséquent surestime la véritable valeur du taux de mortalité de l'épidémie"
        )
    st.altair_chart(c_histo_fatality_rate, use_container_width=True)

st.info(
    """ by: [J. Fourmann](https://www.linkedin.com/in/j%C3%A9r%C3%A9mie-fourmann-7827b859/) | source: [GitHub](https://www.github.com)
        | data source: [Opencovid19-fr (GitHub)]('https://raw.githubusercontent.com/opencovid19-fr/data/master/dist/chiffres-cles.csv'). """
)