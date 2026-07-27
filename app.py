from flask import Flask, request, jsonify, render_template
import tiktoken
from deep_translator import GoogleTranslator
import requests
import time

app = Flask(__name__)
enc = tiktoken.get_encoding("cl100k_base")

SPANISH_WORDS = {"el", "la", "los", "las", "y", "es", "un", "una", "que", "de",
                 "en", "por", "para", "con", "del", "lo", "como", "pero",
                 "sus", "le", "ya", "este", "esta", "muy", "sin", "sobre",
                 "todo", "tambien", "hay", "ser", "son", "tiene", "como"}

PRICING = {
    "openai": {
        "gpt-4o": {"input": 2.50, "output": 10.00, "context": 128000},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60, "context": 128000},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00, "context": 128000},
        "gpt-4": {"input": 30.00, "output": 60.00, "context": 8192},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50, "context": 16385},
        "o1": {"input": 15.00, "output": 60.00, "context": 200000},
        "o1-mini": {"input": 3.00, "output": 12.00, "context": 128000},
    },
    "anthropic": {
        "claude-3.5-sonnet": {"input": 3.00, "output": 15.00, "context": 200000},
        "claude-3.5-haiku": {"input": 0.80, "output": 4.00, "context": 200000},
        "claude-3-opus": {"input": 15.00, "output": 75.00, "context": 200000},
    },
    "google": {
        "gemini-1.5-pro": {"input": 3.50, "output": 10.50, "context": 2000000},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30, "context": 1000000},
        "gemini-1.0-pro": {"input": 0.50, "output": 1.50, "context": 32768},
    },
}

def get_pricing(provider: str, model: str) -> dict | None:
    return PRICING.get(provider, {}).get(model)


def calc_cost(tokens: int, price_per_1m: float) -> float:
    return (tokens / 1_000_000) * price_per_1m


def default_model() -> str:
    return "gpt-4o-mini"


COP_RATE = 4200.0
COP_RATE_CACHE = {"rate": None, "ts": 0}
COP_RATE_TTL = 3600


def get_cop_rate():
    global COP_RATE_CACHE
    now = time.time()
    if COP_RATE_CACHE["rate"] and (now - COP_RATE_CACHE["ts"]) < COP_RATE_TTL:
        return COP_RATE_CACHE["rate"]
    try:
        r = requests.get("https://api.exchangerate.host/latest?base=USD&symbols=COP", timeout=3)
        if r.ok:
            rate = r.json()["rates"]["COP"]
            COP_RATE_CACHE = {"rate": rate, "ts": time.time()}
            return rate
    except Exception:
        pass
    return COP_RATE


def detect_lang(text: str) -> str:
    words = set(text.lower().split())
    return "es" if len(words & SPANISH_WORDS) >= 2 else "en"


def count_tokens(text: str) -> int:
    return len(enc.encode(text))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/translate", methods=["POST"])
def translate():
    data = request.get_json()
    text = data.get("text", "").strip()
    target = data.get("target", "en")
    model = data.get("model", default_model())

    if not text:
        return jsonify({"error": "Texto vacio"}), 400

    pricing = get_pricing("openai", model)
    if not pricing:
        return jsonify({"error": "Modelo no soportado"}), 400

    try:
        translator = GoogleTranslator(source="auto", target=target)
        translated = translator.translate(text)
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500

    source_lang = detect_lang(text)

    orig_tokens = count_tokens(text)
    trans_tokens = count_tokens(translated)
    orig_words = len(text.split())
    trans_words = len(translated.split())

    input_cost = calc_cost(orig_tokens, pricing["input"])
    output_cost = calc_cost(trans_tokens, pricing["output"])
    total_cost = input_cost + output_cost

    return jsonify({
        "original": text,
        "translated": translated,
        "source_lang": source_lang,
        "target_lang": target,
        "model": model,
        "orig_tokens": orig_tokens,
        "trans_tokens": trans_tokens,
        "orig_words": orig_words,
        "trans_words": trans_words,
        "cost": {
            "input": round(input_cost, 6),
            "output": round(output_cost, 6),
            "total": round(total_cost, 6),
            "currency": "USD",
        },
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    text = data.get("text", "").strip()
    mode = data.get("mode", "auto")
    model = data.get("model", default_model())

    if not text:
        return jsonify({"error": "Texto vacio"}), 400

    pricing = get_pricing("openai", model)
    if not pricing:
        return jsonify({"error": "Modelo no soportado"}), 400

    if mode == "auto":
        source_lang = detect_lang(text)
        target_lang = "en" if source_lang == "es" else "es"
        direction_label = f"Auto: {source_lang.upper()}&rarr;{target_lang.upper()}"
    elif mode == "es-en":
        source_lang = "es"
        target_lang = "en"
        direction_label = "ES&rarr;EN"
    elif mode == "en-es":
        source_lang = "en"
        target_lang = "es"
        direction_label = "EN&rarr;ES"
    else:
        return jsonify({"error": "Modo invalido"}), 400

    try:
        translator = GoogleTranslator(source="auto", target=target_lang)
        translated = translator.translate(text)
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500

    orig_tokens = count_tokens(text)
    trans_tokens = count_tokens(translated)
    orig_words = len(text.split())
    trans_words = len(translated.split())

    source_name = "Espanol" if source_lang == "es" else "Ingles"
    target_name = "Espanol" if target_lang == "es" else "Ingles"

    input_cost = calc_cost(orig_tokens, pricing["input"])
    output_cost = calc_cost(trans_tokens, pricing["output"])
    total_cost = input_cost + output_cost

    return jsonify({
        "original": text,
        "translated": translated,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "source_name": source_name,
        "target_name": target_name,
        "direction_label": direction_label,
        "model": model,
        "orig_tokens": orig_tokens,
        "trans_tokens": trans_tokens,
        "orig_words": orig_words,
        "trans_words": trans_words,
        "cost": {
            "input": round(input_cost, 6),
            "output": round(output_cost, 6),
            "total": round(total_cost, 6),
            "currency": "USD",
        },
    })


@app.route("/api/pricing")
def pricing():
    cop = get_cop_rate()
    return jsonify({
        "providers": PRICING,
        "currency": "USD",
        "unit": "per 1M tokens",
        "cop_rate": cop,
        "cop_updated": time.strftime("%H:%M:%S", time.localtime()),
    })




@app.route("/api/compare")
def compare_models():
    cop = get_cop_rate()
    rows = []
    for provider, models in PRICING.items():
        for model_name, info in models.items():
            input_cop = info["input"] * cop
            output_cop = info["output"] * cop
            rows.append({
                "provider": provider,
                "model": model_name,
                "input_usd": info["input"],
                "output_usd": info["output"],
                "input_cop": round(input_cop, 2),
                "output_cop": round(output_cop, 2),
                "context": info["context"],
            })
    rows.sort(key=lambda x: x["input_usd"])
    return jsonify({"models": rows, "cop_rate": cop})

# ─── AGREGAR ESTO ANTES DEL ENDPOINT /api/optimize-prompt ───

import re
from dataclasses import dataclass
from typing import List

@dataclass
class PromptIssue:
    type: str
    severity: str
    description: str
    suggestion: str

@dataclass
class OptimizedPrompt:
    original: str
    optimized: str
    original_tokens: int
    optimized_tokens: int
    token_savings: int
    token_savings_pct: float
    issues_found: List[PromptIssue]
    improvements_applied: List[str]
    estimated_quality_boost: str

class PromptOptimizer:
    VAGUE_WORDS = {
        "mejorar", "mejora", "hacer mejor", "mejor", "optimizar",
        "improve", "better", "optimize", "enhance", "refine",
        "bueno", "buena", "good", "nice", "cool",
        "explicar", "explain", "describe", "talk about",
        "haz algo", "do something", "create something"
    }
    
    NEGATION_PATTERNS = [
        r"\bno\s+(?:uses?|incluyas?|hagas?|pongas?|añadas?)\b",
        r"\bnever\b", r"\bdon['']t\b", r"\bavoid\b",
        r"\bno\s+te\s+olvides\b", r"\brecuerda\s+no\b"
    ]
    
    def __init__(self, target_model: str = "gpt-4o-mini", provider: str = "openai"):
        self.target_model = target_model
        self.provider = provider
    
    def analyze(self, prompt: str) -> List[PromptIssue]:
        issues = []
        prompt_lower = prompt.lower()
        words = set(prompt_lower.split())
        
        vague_found = words & self.VAGUE_WORDS
        if vague_found:
            issues.append(PromptIssue(
                type="vague",
                severity="high",
                description=f"Palabras vagas detectadas: {', '.join(vague_found)}",
                suggestion="Define criterios específicos de éxito. Ej: 'Resume en 3 puntos clave, máx 50 palabras, tono técnico'"
            ))
        
        for pattern in self.NEGATION_PATTERNS:
            if re.search(pattern, prompt_lower):
                issues.append(PromptIssue(
                    type="negative",
                    severity="medium",
                    description="Instrucciones negativas detectadas",
                    suggestion="Refrasea positivamente. Ej: 'Usa solo datos reales' en vez de 'No inventes datos'"
                ))
                break
        
        has_structure = any(marker in prompt_lower for marker in 
                          ["paso", "step", "1.", "2.", "reglas:", "criterios:", 
                           "contexto:", "tarea:", "formato:", "output:"])
        if not has_structure and len(prompt.split()) > 15:
            issues.append(PromptIssue(
                type="no_structure",
                severity="medium",
                description="Prompt largo sin estructura clara",
                suggestion="Usa secciones: TAREA → CONTEXTO → RESTRICCIONES → FORMATO DE SALIDA"
            ))
        
        has_output_format = any(marker in prompt_lower for marker in
                               ["formato", "format", "devuelve", "return", 
                                "json", "markdown", "tabla", "lista"])
        if not has_output_format:
            issues.append(PromptIssue(
                type="missing_context",
                severity="medium",
                description="No se especifica formato de salida",
                suggestion="Define el formato: 'Devuelve JSON con campos: resumen, puntos_clave, accionables'"
            ))
        
        tokens = len(enc.encode(prompt))
        if tokens > 500:
            issues.append(PromptIssue(
                type="too_long",
                severity="low",
                description=f"Prompt muy largo ({tokens} tokens)",
                suggestion="Coloca la tarea principal en las primeras líneas. Elimina contexto redundante."
            ))
        
        return issues
    
    def optimize(self, prompt: str, purpose: str = "translate") -> OptimizedPrompt:
        issues = self.analyze(prompt)
        original_tokens = len(enc.encode(prompt))
        
        optimized = self._apply_optimizations(prompt, issues)
        optimized_tokens = len(enc.encode(optimized))
        
        savings = original_tokens - optimized_tokens
        savings_pct = (savings / original_tokens * 100) if original_tokens > 0 else 0
        
        severity_score = sum({
            "low": 1, "medium": 2, "high": 3
        }[i.severity] for i in issues)
        
        quality_boost = "alta" if severity_score >= 6 else ("media" if severity_score >= 3 else "baja")
        improvements = [i.suggestion for i in issues]
        
        return OptimizedPrompt(
            original=prompt,
            optimized=optimized,
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            token_savings=max(0, savings),
            token_savings_pct=max(0, savings_pct),
            issues_found=issues,
            improvements_applied=improvements,
            estimated_quality_boost=quality_boost
        )
    
    def _apply_optimizations(self, prompt: str, issues: List[PromptIssue]) -> str:
        optimized = prompt.strip()
        
        if self.provider == "anthropic":
            optimized = self._structure_for_claude(optimized, issues)
        elif self.provider == "google":
            optimized = self._structure_for_gemini(optimized, issues)
        else:
            optimized = self._structure_for_openai(optimized, issues)
        
        return optimized
    
    def _structure_for_openai(self, prompt: str, issues: List[PromptIssue]) -> str:
        parts = []
        is_reasoning = self.target_model.startswith(("o1", "o3"))
        
        task = self._extract_task(prompt)
        parts.append(f"TAREA: {task}")
        
        context = self._extract_context(prompt)
        if context:
            parts.append(f"\nCONTEXTO:\n{context}")
        
        criteria = self._generate_criteria(prompt, issues)
        if criteria:
            parts.append(f"\nCRITERIOS:\n{criteria}")
        
        output_format = self._generate_output_format(prompt)
        parts.append(f"\nFORMATO DE SALIDA:\n{output_format}")
        
        constraints = self._generate_positive_constraints(issues)
        if constraints:
            parts.append(f"\nRESTRICCIONES:\n{constraints}")
        
        if not is_reasoning and any(i.type in ["vague", "no_structure"] for i in issues):
            parts.append("\nRazona paso a paso antes de responder.")
        
        return "\n".join(parts)
    
    def _structure_for_claude(self, prompt: str, issues: List[PromptIssue]) -> str:
        parts = []
        task = self._extract_task(prompt)
        parts.append(f"<tarea>\n{task}\n</tarea>")
        
        context = self._extract_context(prompt)
        if context:
            parts.append(f"\n<contexto>\n{context}\n</contexto>")
        
        criteria = self._generate_criteria(prompt, issues)
        if criteria:
            parts.append(f"\n<criterios>\n{criteria}\n</criterios>")
        
        output_format = self._generate_output_format(prompt)
        parts.append(f"\n<formato_salida>\n{output_format}\n</formato_salida>")
        
        constraints = self._generate_positive_constraints(issues)
        if constraints:
            parts.append(f"\n<restricciones>\n{constraints}\n</restricciones>")
        
        return "\n".join(parts)
    
    def _structure_for_gemini(self, prompt: str, issues: List[PromptIssue]) -> str:
        task = self._extract_task(prompt)
        parts = [task]
        
        context = self._extract_context(prompt)
        if context and len(context.split()) < 50:
            parts.append(f"\nContexto: {context}")
        
        output_format = self._generate_output_format(prompt, simple=True)
        parts.append(f"\nFormato: {output_format}")
        
        return "\n".join(parts)
    
    def _extract_task(self, prompt: str) -> str:
        sentences = re.split(r'[.!?]\s+', prompt)
        task = sentences[0] if sentences else prompt
        return task[:200] if len(task) > 200 else task
    
    def _extract_context(self, prompt: str) -> str:
        sentences = re.split(r'[.!?]\s+', prompt)
        if len(sentences) > 1:
            return " ".join(sentences[1:]).strip()
        return ""
    
    def _generate_criteria(self, prompt: str, issues: List[PromptIssue]) -> str:
        criteria = []
        if any(i.type == "vague" for i in issues):
            criteria.append("- Sé específico: define métricas medibles")
        
        spanish_words = {"el", "la", "los", "de", "en", "y", "que"}
        is_spanish = len(set(prompt.lower().split()) & spanish_words) > 2
        
        if is_spanish:
            criteria.extend([
                "- Mantén el significado original",
                "- Usa lenguaje claro y directo",
                "- Evita ambigüedades"
            ])
        else:
            criteria.extend([
                "- Preserve original meaning",
                "- Use clear, direct language",
                "- Avoid ambiguity"
            ])
        
        return "\n".join(criteria) if criteria else ""
    
    def _generate_output_format(self, prompt: str, simple: bool = False) -> str:
        if simple:
            return "Texto plano, conciso"
        
        code_keywords = {"código", "code", "función", "function", "python", "javascript"}
        if any(kw in prompt.lower() for kw in code_keywords):
            return "Bloque de código con comentarios explicativos"
        
        return "Respuesta estructurada con secciones claras"
    
    def _generate_positive_constraints(self, issues: List[PromptIssue]) -> str:
        constraints = []
        for issue in issues:
            if issue.type == "negative":
                constraints.append("- Usa solo información verificable")
                constraints.append("- Basado únicamente en el contexto proporcionado")
            elif issue.type == "vague":
                constraints.append("- Responde solo lo solicitado, sin información extra")
        
        return "\n".join(constraints) if constraints else ""


def optimize_prompt_for_api(text: str, model: str = "gpt-4o-mini") -> dict:
    provider = "openai"
    if "claude" in model.lower():
        provider = "anthropic"
    elif "gemini" in model.lower():
        provider = "google"
    
    optimizer = PromptOptimizer(target_model=model, provider=provider)
    result = optimizer.optimize(text)
    
    return {
        "original": result.original,
        "optimized": result.optimized,
        "original_tokens": result.original_tokens,
        "optimized_tokens": result.optimized_tokens,
        "token_savings": result.token_savings,
        "token_savings_pct": round(result.token_savings_pct, 1),
        "issues_found": [
            {
                "type": issue.type,
                "severity": issue.severity,
                "description": issue.description,
                "suggestion": issue.suggestion
            }
            for issue in result.issues_found
        ],
        "improvements_applied": result.improvements_applied,
        "estimated_quality_boost": result.estimated_quality_boost,
        "provider_strategy": provider
    }


@app.route("/api/optimize-prompt", methods=["POST"])
def optimize_prompt():
    """
    Endpoint para optimizar prompts antes de traducir.
    Devuelve el prompt mejorado + análisis de ahorro.
    """
    data = request.get_json()
    text = data.get("text", "").strip()
    model = data.get("model", default_model())

    if not text:
        return jsonify({"error": "Texto vacio"}), 400

    try:
        result = optimize_prompt_for_api(text, model)
        
        # Calcular costos comparativos
        pricing = get_pricing("openai", model)
        if pricing:
            orig_cost = calc_cost(result["original_tokens"], pricing["input"])
            opt_cost = calc_cost(result["optimized_tokens"], pricing["input"])
            result["cost_original"] = round(orig_cost, 6)
            result["cost_optimized"] = round(opt_cost, 6)
            result["cost_savings"] = round(orig_cost - opt_cost, 6)
            result["cost_savings_pct"] = round((orig_cost - opt_cost) / orig_cost * 100, 1) if orig_cost > 0 else 0
        
        return jsonify(result)
        
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500

if __name__ == "__main__":
    import subprocess
    import signal
    import os

    PORT = 8080

    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        subprocess.run(["fuser", "-k", f"{PORT}/tcp"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def shutdown(sig, frame):
        print(f"\nPuerto {PORT} liberado.")
        os._exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print(f"Servidor corriendo en http://localhost:{PORT}")
    app.run(debug=True, port=PORT)