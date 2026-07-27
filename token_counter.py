import tiktoken
from deep_translator import GoogleTranslator

enc = tiktoken.get_encoding("cl100k_base")
traductor = GoogleTranslator(source="auto", target="en")

def contar(texto):
    return len(enc.encode(texto))

original = input("Texto: ")
traducido = traductor.translate(original)

to_orig = contar(original)
to_trad = contar(traducido)

print(f"Original  : {original}  ({to_orig} tokens)")
print(f"Traducido : {traducido}  ({to_trad} tokens)")
print(f"Diferencia: {to_trad - to_orig:+d} tokens ({(to_trad/to_orig - 1)*100:+.1f}%)")
