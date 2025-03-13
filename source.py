import pandas as pd
from datetime import datetime
import json
import requests
from haversine import haversine, Unit
import pandas as pd
import numpy as np


# Função para converter todos os np.int64 em int
def converter_int(obj):
    if isinstance(obj, np.int64):
        return int(obj)
    if isinstance(obj, dict):
        return {k: converter_int(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [converter_int(i) for i in obj]
    return obj


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


def ordenar_por_classe(pai):
    if pai["classe"] == "baixa":
        classe_peso = 0
    elif pai["classe"] == "média":
        classe_peso = 1
    else: 
        classe_peso = 2

    return (classe_peso, -len(pai["Filhos"]))


data = pd.read_csv("pessoas.csv", dtype=str)
data_escolas = pd.read_csv("escolas.csv", dtype=str)
notas = pd.read_csv("saeb.csv", dtype=str)
# transporte = pd.read_csv("transporte.csv", dtype=str)
transporte = pd.read_csv("transporte.csv", sep=";")

data["Data de nascimento"] = pd.to_datetime(data["Data de nascimento"], format="%d/%m/%Y", errors="coerce")

ano_atual = datetime.now().year
Dados_Dos_Pais = []
escolas_com_vagas = []

for _, pai in data[data["Tem filhos"] == "TRUE"].iterrows():
    cpf_pai = pai["CPF"]

    filhos = data[
        ((data["CPF do Pai"] == cpf_pai) | (data["CPF da Mae"] == cpf_pai)) & (data["Data de nascimento"].dt.year == ano_atual - 6)
    ]

    if not filhos.empty:
        cep = pai["CEP"]
        endereco = get_address_from_cep(cep)
        Dados_Dos_Pais.append({
            "Nome do Pai/Mãe": pai["Nome"],
            "classe": pai['Classe'],
            "Filhos": filhos["Nome"].tolist(),
            "Número de Telefone": pai["Numero de telefone"],
            "CEP": cep,
            "Endereco": endereco,
        })


Dados_Dos_Pais.sort(key=ordenar_por_classe)


for dados in Dados_Dos_Pais:
    cpf_pai = dados["Nome do Pai/Mãe"]  
    cep = dados["CEP"]
    endereco = get_address_from_cep(cep)

    lat_pai = float(endereco["lat"])
    lon_pai = float(endereco["lng"])

    escolas_proximas = []
    for _, escola in data_escolas.iterrows():
        # Verifique a quantidade de vagas na escola
        vagas_disponiveis = escola["vagas"]
        vagas_disponiveis = float(vagas_disponiveis)

        if (pd.isna(vagas_disponiveis) or vagas_disponiveis >= 1) and not pd.isna(escola["tipo"]) and "CRECHE" not in escola["tipo"] and not pd.isna(escola["tipo"]) and "CMEI" not in escola["tipo"] :
            lat_escola = float(escola["latitude"])
            lon_escola = float(escola["longitude"])
            distancia = calcular_distancia(lat_pai, lon_pai, lat_escola, lon_escola)

            # Adiciona as informações da escola na lista escolas_proximas
            escolas_proximas.append({
                "Nome da Escola": escola["escola"],
                "Tipo": escola['tipo'],
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
                "Gestor": escola["gestor"], 
                "Índice": _,  
            })

            # escola["vagas"] = vagas_disponiveis - 0.3333333  # Diminui uma vaga

    escolas_proximas.sort(key=lambda x: x["Distância (km)"])
    for i in range(min(3, len(escolas_proximas))):  
        idx = escolas_proximas[i]["Índice"]  
        data_escolas.at[idx, "vagas"] = max(0, float(data_escolas.at[idx, "vagas"]) - 0.3333333)  # Garante que não fique negativo
    for escola in escolas_proximas:
        del escola["Índice"]


    for escola in escolas_proximas[:3]:

        nome_escola = escola['Nome da Escola']
        prefixo = escola['Tipo']

        Nome_completo = f'{prefixo} {nome_escola}'

        linha_escola = notas[notas.iloc[:, 4].str.contains(nome_escola, na=False, case=False)]

        if not linha_escola.empty:
            valor_coluna_103 = linha_escola.iloc[0, 103]
            valor_coluna_104 = linha_escola.iloc[0, 104]
            valor_coluna_105 = linha_escola.iloc[0, 105]

            escola["Nota SAEB - 2023 Matemática"] = valor_coluna_103
            escola["Nota SAEB - 2023 Portugues"] = valor_coluna_104
            escola["Nota SAEB - 2023 Media"] = valor_coluna_105
        else:
            escola["Nota SAEB"] = 'Não existe dados do SAEB para essa escola'
            print(f"Nota no SAEB da Escola {nome_escola} não encontrada.")

        # "transporte" 
        linha_transporte = transporte[transporte['escolas'].str.contains(Nome_completo, na=False, case=False)]
        if not linha_transporte.empty:
            escola["Transporte - Manhã"] = linha_transporte.iloc[0]['manha']
            escola["Transporte - Tarde"] = linha_transporte.iloc[0]['tarde']
            escola["Transporte - Noite"] = linha_transporte.iloc[0]['noite']
        else:
            escola["Transporte"] = "Não há dados de transporte publico para essa escola"

    dados["Escolas Proximas"] = escolas_proximas[:3]


# Converter antes de serializar
Dados_Dos_Pais_convertido = converter_int(Dados_Dos_Pais)

print(json.dumps(Dados_Dos_Pais_convertido, indent=4, ensure_ascii=False))

#############################################

Dados_Dos_Pais = []
escolas_com_vagas = []

for _, pai in data[data["Tem filhos"] == "TRUE"].iterrows():
    cpf_pai = pai["CPF"]

    filhos = data[
        ((data["CPF do Pai"] == cpf_pai) | (data["CPF da Mae"] == cpf_pai)) & (data["Data de nascimento"].dt.year == ano_atual - 2)
    ]

    if not filhos.empty:
        cep = pai["CEP"]
        endereco = get_address_from_cep(cep)
        Dados_Dos_Pais.append({
            "Nome do Pai/Mãe": pai["Nome"],
            "classe": pai['Classe'],
            "Filhos": filhos["Nome"].tolist(),
            "Número de Telefone": pai["Numero de telefone"],
            "CEP": cep,
            "Endereco": endereco,
        })


Dados_Dos_Pais.sort(key=ordenar_por_classe)


for dados in Dados_Dos_Pais:
    cpf_pai = dados["Nome do Pai/Mãe"]  
    cep = dados["CEP"]
    endereco = get_address_from_cep(cep)

    lat_pai = float(endereco["lat"])
    lon_pai = float(endereco["lng"])

    escolas_proximas = []
    for _, escola in data_escolas.iterrows():
        # Verifique a quantidade de vagas na escola
        vagas_disponiveis = escola["vagas"]
        vagas_disponiveis = float(vagas_disponiveis)

        if (pd.isna(vagas_disponiveis) or vagas_disponiveis >= 1) and not pd.isna(escola["tipo"]) and "ESCOLA" not in escola["tipo"]:
            lat_escola = float(escola["latitude"])
            lon_escola = float(escola["longitude"])
            distancia = calcular_distancia(lat_pai, lon_pai, lat_escola, lon_escola)

            # Adiciona as informações da escola na lista escolas_proximas
            escolas_proximas.append({
                "Nome da Escola": escola["escola"],
                "Tipo": escola['tipo'],
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
                "Gestor": escola["gestor"], 
                "Índice": _,  
            })
            
            # Atualiza a quantidade de vagas no CSV, diminuindo 1 vaga
            #escola["vagas"] = vagas_disponiveis - 0.3333333  # Diminui uma vaga

    escolas_proximas.sort(key=lambda x: x["Distância (km)"])
    for i in range(min(3, len(escolas_proximas))):  
        idx = escolas_proximas[i]["Índice"]  
        data_escolas.at[idx, "vagas"] = max(0, float(data_escolas.at[idx, "vagas"]) - 0.3333333)  # Garante que não fique negativo
    for escola in escolas_proximas:
        del escola["Índice"]

    for escola in escolas_proximas[:3]:
        nome_escola = escola['Nome da Escola']
        linha_escola = notas[notas.iloc[:, 4].str.contains(nome_escola, na=False, case=False)]

        prefixo = escola['Tipo']

        Nome_completo = f'{prefixo} {nome_escola}'

        if not linha_escola.empty:
            valor_coluna_103 = linha_escola.iloc[0, 103]
            valor_coluna_104 = linha_escola.iloc[0, 104]
            valor_coluna_105 = linha_escola.iloc[0, 105]

            escola["Nota SAEB - 2023 Matemática"] = valor_coluna_103
            escola["Nota SAEB - 2023 Portugues"] = valor_coluna_104
            escola["Nota SAEB - 2023 Media"] = valor_coluna_105
        else:
            escola["Nota SAEB"] = 'Não existe dados do SAEB para essa escola'
            print(f"Nota no SAEB da Escola {nome_escola} não encontrada.")

        # "transporte" 
        linha_transporte = transporte[transporte['escolas'].str.contains(Nome_completo, na=False, case=False)]
        
        if not linha_transporte.empty:
            escola["Transporte - Manhã"] = linha_transporte.iloc[0]['manha']
            escola["Transporte - Tarde"] = linha_transporte.iloc[0]['tarde']
            escola["Transporte - Noite"] = linha_transporte.iloc[0]['noite']
        else:
            escola["Transporte"] = "Não há dados de transporte publico para essa escola"

    dados["Escolas Proximas"] = escolas_proximas[:3]


# Converter antes de serializar
Dados_Dos_Pais_convertido = converter_int(Dados_Dos_Pais)

print(json.dumps(Dados_Dos_Pais_convertido, indent=4, ensure_ascii=False))
