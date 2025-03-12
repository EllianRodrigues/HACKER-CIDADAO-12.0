import pandas as pd
from datetime import datetime
import json
import requests
from haversine import haversine, Unit
import pandas as pd

def get_address_from_cep(cep):
    url = f"https://cep.awesomeapi.com.br/json/{cep}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return {}


def calcular_distancia(lat1, lon1, lat2, lon2):
    ponto1 = (lat1, lon1)
    ponto2 = (lat2, lon2)
    return haversine(ponto1, ponto2, unit=Unit.KILOMETERS)


data = pd.read_csv("pessoas.csv", dtype=str)
data_escolas = pd.read_csv("escolas.csv", dtype=str)
notas = pd.read_csv("saeb.csv", dtype=str)

data["Data de nascimento"] = pd.to_datetime(data["Data de nascimento"], format="%d/%m/%Y", errors="coerce")

ano_atual = datetime.now().year
Dados_Dos_Pais = []

for _, pai in data[data["Tem filhos"] == "TRUE"].iterrows():
    cpf_pai = pai["CPF"]

    filhos = data[
        ((data["CPF do Pai"] == cpf_pai) | (data["CPF da Mae"] == cpf_pai)) & (data["Data de nascimento"].dt.year == ano_atual - 6)
    ]

    if not filhos.empty:
        cep = pai["CEP"]
        endereco = get_address_from_cep(cep)
        
        lat_pai = float(endereco["lat"])
        lon_pai = float(endereco["lng"])

        escolas_proximas = []
        
        for _, escola in data_escolas.iterrows():
            lat_escola = float(escola["latitude"])
            lon_escola = float(escola["longitude"])
            distancia = calcular_distancia(lat_pai, lon_pai, lat_escola, lon_escola)

            escolas_proximas.append({
                "Nome da Escola": escola["escola"],
                "Distância (km)": round(distancia, 1),
                "Rua": escola["rua"],  
                "Número": escola["numero"], 
                "Bairro": escola["bairro"], 
                "Qtd Alunos": escola["qtd_alunos"], 
                "Qtd Turmas": escola["qtd_turmas"], 
                "Qtd Professores": escola["qtd_professores"], 
                "Escola Climatizada": escola["escola_climatizada"],  
                "Data Visita": escola["data_visita"],  
                "Quadra Coberta": escola["quadra_coberta"],  
                "Quadra Descoberta": escola["quadra_descoberta"],  
                "Biblioteca": escola["biblioteca"],  
                "Sala Recurso": escola["sala_recurso"],  
                "Gestor": escola["gestor"] 
            })

        
        escolas_proximas.sort(key=lambda x: x["Distância (km)"]) # Ordena as escolas pela distância (mais próxima primeiro)
        
        for escola in escolas_proximas[:3]:
            nome_escola = escola['Nome da Escola']       
            linha_escola = notas[notas.iloc[:, 4].str.contains(nome_escola, na=False, case=False)]

            if not linha_escola.empty:

                valor_coluna_103 = linha_escola.iloc[0, 103]
                valor_coluna_104 = linha_escola.iloc[0, 104]
                valor_coluna_105 = linha_escola.iloc[0, 105]

                escola["Nota SAEB - 2023 Matemática"] = valor_coluna_103
                escola["Nota SAEB - 2023 Portugues"] = valor_coluna_104
                escola["Nota SAEB - 2023 Media"] = valor_coluna_105
            else:
                print(f"Escola {nome_escola} não encontrada.")
        


        Dados_Dos_Pais.append({
            "Nome do Pai/Mãe": pai["Nome"],
            "Filhos": filhos["Nome"].tolist(),
            "Número de Telefone": pai["Numero de telefone"],
            "CEP": cep,
            "Endereco": endereco,
            "Escolas Proximas": escolas_proximas[:3] 
        })


print(json.dumps(Dados_Dos_Pais, indent=4, ensure_ascii=False))
