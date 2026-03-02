from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/report/<int:value>")
def report(value):
    return jsonify({
        "input": value,
        "result": value * 10
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)