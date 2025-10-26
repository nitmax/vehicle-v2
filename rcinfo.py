from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import requests
import re

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36",
    "Referer": "https://vahanx.in/",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br"
}

@app.route("/api/vehicle-info", methods=["GET"])
def get_vehicle_info():
    rc = request.args.get("rc")
    if not rc:
        return jsonify({"error": "Missing rc parameter"}), 400

    try:
        url = f"https://vahanx.in/rc-search/{rc}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        def extract_card(label):
            for div in soup.select(".hrcd-cardbody"):
                span = div.find("span")
                if span and label.lower() in span.text.lower():
                    return div.find("p").get_text(strip=True)
            return ""

        def extract_from_section(header_text, keys):
            section = soup.find("h3", string=lambda s: s and header_text.lower() in s.lower())
            section_card = section.find_parent("div", class_="hrc-details-card") if section else None
            result = {}
            for key in keys:
                span = section_card.find("span", string=lambda s: s and key in s) if section_card else None
                if span:
                    val = span.find_next("p")
                    result[key.lower().replace(" ", "_")] = val.get_text(strip=True) if val else ""
            return result

        registration_number = soup.find("h1").text.strip()
        modal_name = extract_card("Modal Name")
        owner_name = extract_card("Owner Name")
        code = extract_card("Code")
        city = extract_card("City Name")
        phone = extract_card("Phone")
        website = extract_card("Website")
        address = extract_card("Address")

        ownership = extract_from_section("Ownership Details", [
            "Owner Name", "Owner Serial No", "Registration Number", "Registered RTO"
        ])

        vehicle = extract_from_section("Vehicle Details", [
            "Model Name", "Maker Model", "Vehicle Class", "Fuel Type", "Fuel Norms"
        ])

        insurance_expired_box = soup.select_one(".insurance-alert-box.expired .title")
        expired_days = int(re.search(r"(\d+)", insurance_expired_box.text).group(1)) if insurance_expired_box else None
        insurance = extract_from_section("Insurance Information", ["Insurance Expiry"])
        insurance = {
            "status": "Expired",
            "expiry_date": insurance.get("insurance_expiry", ""),
            "expired_days_ago": expired_days
        }

        validity = extract_from_section("Important Dates", [
            "Registration Date", "Vehicle Age", "Fitness Upto", "Insurance Upto", "Insurance Expiry In"
        ])

        other = extract_from_section("Other Information", [
            "Financer Name", "Cubic Capacity", "Seating Capacity", "Permit Type", "Blacklist Status", "NOC Details"
        ])

        data = {
            "registration_number": registration_number,
            "modal_name": modal_name,
            "owner_name": owner_name,
            "code": code,
            "city": city,
            "phone": phone,
            "website": website,
            "address": address,
            "ownership_details": {
                "owner_name": ownership.get("owner_name", ""),
                "serial_no": ownership.get("owner_serial_no", ""),
                "rto": ownership.get("registered_rto", "")
            },
            "vehicle_details": {
                "maker": vehicle.get("model_name", ""),
                "model": vehicle.get("maker_model", ""),
                "vehicle_class": vehicle.get("vehicle_class", ""),
                "fuel_type": vehicle.get("fuel_type", ""),
                "fuel_norms": vehicle.get("fuel_norms", "")
            },
            "insurance": insurance,
            "validity": {
                "registration_date": validity.get("registration_date", ""),
                "vehicle_age": validity.get("vehicle_age", ""),
                "fitness_upto": validity.get("fitness_upto", ""),
                "insurance_upto": validity.get("insurance_upto", ""),
                "insurance_status": validity.get("insurance_expiry_in", "")
            },
            "other_info": {
                "financer": other.get("financer_name", ""),
                "cubic_capacity": other.get("cubic_capacity", ""),
                "seating_capacity": other.get("seating_capacity", ""),
                "permit_type": other.get("permit_type", ""),
                "blacklist_status": other.get("blacklist_status", ""),
                "noc": other.get("noc_details", "")
            }
        }

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=8888, debug=True)