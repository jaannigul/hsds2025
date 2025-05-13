from flask import Flask
from flask import request
import os
import json
import requests
from azure.storage.blob import BlobServiceClient
import re
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

def otsi_sone_parem(tekst, sone):
    pattern = re.compile(rf"\b{re.escape(sone)}\b", flags=re.IGNORECASE)
    return len(pattern.findall(tekst))

@app.route("/raamatu_otsing/<int:raamatu_id>", methods=["POST"])
def raamatust_sone_otsimine(raamatu_id):
    input_data = request.get_json(force=True)
    sone = input_data.get("sone")
    if not sone:
        return {"error": "Puudub võti 'sone'"}, 400

    try:
        content = blob_alla_laadimine(f"{raamatu_id}.txt")
    except Exception:
        return {}, 404

    total_found = otsi_sone_parem(content, sone)
    return {
        "raamatu_id": raamatu_id,
        "sone": sone,
        "leitud": total_found
    }, 200

@app.route("/raamatu_otsing/", methods=["POST"])
def otsi_sone_raamatutes():
    input_data = request.get_json(force=True)
    sone = input_data.get("sone")
    if not sone:
        return {"error": "Puudub võti 'sone'"}, 400

    tulemused = []
    container_client = blob_service_client.get_container_client(blob_container_name)

    for blob_props in container_client.list_blobs():
        blob_name = blob_props.name
        if not blob_name.lower().endswith(".txt"):
            continue

        try:
            content = blob_alla_laadimine(blob_name)
        except Exception:
            continue

        count = otsi_sone_parem(content, sone)
        if count > 0:
            raamatu_id = os.path.splitext(os.path.basename(blob_name))[0]
            tulemused.append({"raamatu_id": int(raamatu_id), "leitud": count})

    return {
        "sone": sone,
        "tulemused": tulemused
    }, 200



def blob_konteineri_loomine(konteineri_nimi):
    container_client = blob_service_client.get_container_client(container=konteineri_nimi)
    if not container_client.exists():
        blob_service_client.create_container(konteineri_nimi)


def blob_alla_laadimine(faili_nimi):
    blob_client = blob_service_client.get_blob_client(container=blob_container_name, blob=faili_nimi)
    return blob_client.download_blob().content_as_text()


blob_connection_string = os.getenv('APPSETTING_AzureWebJobsStorage')
blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
blob_container_name = os.getenv('APPSETTING_blob_container_name')
blob_konteineri_loomine(blob_container_name)
if __name__ == '__main__':
    app.run(debug = True, port=5002)
