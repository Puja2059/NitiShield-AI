import re

from flask import Flask, jsonify, request

from search_engine import LegalSearchEngine


app = Flask(__name__)
search_engine = None
GREETING_PATTERN = re.compile(
	 r"^(hello|hi|hey|namaste)( there)?[!.?]*$",
	 re.IGNORECASE,
)


def get_search_engine():
	global search_engine

	if search_engine is None:
		search_engine = LegalSearchEngine()

	return search_engine


@app.post("/api/search")
def search():
	payload = request.get_json(silent=True)

	if not isinstance(payload, dict):
		return jsonify({"error": "Request body must be a JSON object."}), 400

	question = payload.get("question")

	if not isinstance(question, str) or not question.strip():
		return jsonify({"error": "Question must be a non-empty string."}), 400

	question = question.strip()

	if GREETING_PATTERN.fullmatch(question):
		return jsonify({
			"question": question,
			"answer": (
				"Hello! I can help you search legal information "
				"from the provided documents and trusted external sources."
			),
			"source": "assistant",
			"results": [],
		})

	try:
		results = get_search_engine().hybrid_search(question)
	except Exception:
		app.logger.exception("Legal search failed")
		return jsonify({"error": "Legal search failed."}), 500

	return jsonify({
		"question": question,
		"source": (
			"external"
			if results and results[0].get("retrieval_method") == "external"
			else "local_documents"
		),
		"results": results,
	})


if __name__ == "__main__":
	app.run(host="127.0.0.1", port=5000, debug=True)
