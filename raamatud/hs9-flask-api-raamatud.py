from flask import Flask
from flask import request
import os
import json
import requests
from azure.storage.blob import BlobServiceClient
from flask_cors import CORS
app = Flask(__name__)
cors = CORS(app, resources={r"/raamatud/*": {"origins": "*"}, r"/raamatu_otsing/*": {"origins": "*"}})
# Kaust, kuhu see programm hakkab raamatute faile salvestama.
# Raamatute nimed peaksid olema formaadis:  Gutenberg_ID.txt : Näiteks "12345.txt"
raamatute_kaust = "./raamatud"

def lae_alla_raamat(gutenberg_id):
    url = f"https://www.gutenberg.org/cache/epub/{gutenberg_id}/pg{gutenberg_id}.txt"
    response = requests.get(url)
    with open(f"raamatud/{gutenberg_id}.txt","w+", encoding="utf-8") as f:
        f.write(response.text)

def otsi_sone(gutenberg_id, sone):
    sum = 0
    try:
        with open(os.path.join(raamatute_kaust, f"{gutenberg_id}.txt"),"r", encoding="utf-8") as f:
            content = f.read()

            for line in content.splitlines():
                count_in_line = line.lower().split().count(sone.lower())
                if count_in_line > 0:
                    sum += count_in_line
    except FileNotFoundError:
        return -1

    return sum

# Python meetodi definitsioon, mis implementeerib REST meetodi
# app.route(REST_ENDPOINT, methods) määrab ära milliseid REST/HTTP päringuid sellele meetodile edastatakse/suunatakse
# Siin näites on selleks: GET meetodi saatmine REST lõpp-punkti "/raamatud".
#      Ehk, Kui saadetakse GET päring aadressile "http://localhost:5000/raamatud", siis käivitatakse see meetod.
# Päringu vatusena saadetakse tagasi misiganes see meetod tagastab return operatsiooni tulemusena.
@app.route('/raamatud/', methods=['GET'])
def raamatu_nimekiri():
    """
    GET /raamatud
    Tagastab blob konteineri failinimed/raamatud listina JSON kujul
    """
    try:
        raamatud = blob_raamatute_nimekiri()
        raamatud_clean = [name[:-4] for name in raamatud if name.endswith('.txt')]
        return ({"raamatud": raamatud_clean}, 200)
    except Exception as e:
        return ({"error": str(e)}, 500)


@app.route('/raamatud/<book_id>', methods=['GET'])
def raamatu_allatombamine(book_id):
    """
    GET /raamatud/<book_id>
    Laadib alla raamatu (blob) sisu Azure’ist.
    Tagastab selle tekstina (plain text).
    """
    blob_name = book_id + ".txt"
    try:
        raamatu_sisu = blob_alla_laadimine(blob_name)
        return (
            raamatu_sisu,
            200,
            {'Content-Type': 'text/plain; charset=utf-8'}
        )
    except Exception:
        return ({}, 404)


@app.route('/raamatud/<book_id>', methods=['DELETE'])
def raamatu_kustutamine(book_id):
    """
    DELETE /raamatud/<book_id>
    Kustutab raamatu (blob) konteinerist
    """
    blob_name = book_id + ".txt"
    try:
        blob_kustutamine(blob_name)
        return ({}, 204)
    except Exception:
        return ({}, 404)


@app.route('/raamatud/', methods=['POST'])
def raamatu_lisamine():
    input_data = json.loads(request.data)
    book_id = str(input_data['raamatu_id'])
    blob_name = book_id + ".txt"

    try:
        url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
        response = requests.get(url)
        response.raise_for_status()

        blob_ules_laadimine_sisu(blob_name, response.text)

        return ({
            "tulemus": "Raamatu loomine õnnestus",
            "raamatu_id": book_id
        }, 201)
    except requests.exceptions.HTTPError:
        return ({"error": "Gutenbergist raamatu laadimine ebaõnnestus."}, 400)
    except Exception as e:
        return ({"error": str(e)}, 400)




def blob_konteineri_loomine(konteineri_nimi):
    container_client = blob_service_client.get_container_client(container=konteineri_nimi)
    if not container_client.exists():
        blob_service_client.create_container(konteineri_nimi)

def blob_raamatute_nimekiri():
    container_client = blob_service_client.get_container_client(container=blob_container_name)
    blob_names = []
    for blob in container_client.list_blobs():
        blob_names.append(blob.name)
    return blob_names

def blob_alla_laadimine(faili_nimi):
    blob_client = blob_service_client.get_blob_client(container=blob_container_name, blob=faili_nimi)
    return blob_client.download_blob().content_as_text()

def blob_ules_laadimine_sisu(faili_nimi, sisu):
    blob_client = blob_service_client.get_blob_client(container=blob_container_name, blob=faili_nimi)
    blob_client.upload_blob(sisu, overwrite=True)

def blob_kustutamine(faili_nimi):
    blob_client = blob_service_client.get_blob_client(container=blob_container_name, blob=faili_nimi)
    blob_client.delete_blob()

blob_connection_string = os.getenv('APPSETTING_AzureWebJobsStorage')
blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
blob_container_name = os.getenv('APPSETTING_blob_container_name')
blob_konteineri_loomine(blob_container_name)
if __name__ == '__main__':
    app.run(debug = True, port=5001)
