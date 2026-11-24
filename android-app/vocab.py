"""Tira o vocabulário do modelo de voz (Vosk) para o app: python3 vocab.py modelo.zip saida.txt

O assistente sempre ligado usa uma gramática; palavra fora do vocabulário do modelo é ignorada pelo Vosk. Com a lista,
o app sabe quais nomes de cidade dá para reconhecer e escreve os outros com pedaços que existem ("Guidoval" → "guido val").
O vocabulário fica na tabela de símbolos de saída do Gr.fst (formato da OpenFst): nome da tabela, int64 próxima chave,
int64 quantidade e, para cada símbolo, int32 tamanho + texto UTF-8 + int64 chave."""
import re, struct, sys, zipfile

NAME = b'exp/chain/tdnn/lgraph/words.txt'


def words_from_fst(b):
    i = b.find(NAME)
    if i < 0:
        raise SystemExit('tabela de palavras não encontrada no Gr.fst')
    p = i + len(NAME)
    _, n = struct.unpack_from('<qq', b, p)
    p += 16
    if not 1000 < n < 2_000_000:
        raise SystemExit('quantidade de palavras estranha: %d' % n)
    out = []
    for _ in range(n):
        ln = struct.unpack_from('<i', b, p)[0]
        p += 4
        w = b[p:p + ln].decode('utf-8', 'replace')
        p += ln + 8
        if re.fullmatch(r'[a-zà-ÿ]{1,20}', w):
            out.append(w)
    return out


def main(zpath, out):
    with zipfile.ZipFile(zpath) as z:
        name = next(n for n in z.namelist() if n.endswith('/Gr.fst'))
        ws = words_from_fst(z.read(name))
    open(out, 'w', encoding='utf-8').write('\n'.join(ws) + '\n')
    print('vocabulário do modelo de voz: %d palavras' % len(ws))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
