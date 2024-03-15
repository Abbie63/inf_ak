from itertools import chain
import pprint
import json

def unwrap(f):
    def unwrapped(src):
        for val, rst in f(src):
            yield val[0], rst
            return
    unwrapped.__name__ = f"unwrapped_{f.__name__}"
    return unwrapped

def sequence(*fns):
    def result(src):
        results = []
        for f in fns:
            failed = True
            for (v, rst) in f(src):
                failed = False
                if v is not None:
                    results.append(v)
                src = rst
            if failed:
                return
        yield results, src
        return
    return result

def parse_to_word(word):
    def parser(src):
        idx = src.find(word)
        if idx != -1:
            yield src[:idx], src[idx:]
            return
    parser.__name__ = f"parse_to_{word}"
    return parser

def optional(f):
    def result(src):
        for (v, rst) in f(src):
            yield v, rst
            return
        yield None, src
        return
    return result

def parse_indent(src):
    for (idx, c) in enumerate(src):
        if c != ' ':
            yield idx, src[idx:]
            return
        

def parse_array(src):
    for idnt, rst in sequence(
        parse_indent,
        ignore_word('- '),
    )(src):
        idnt = idnt[0]
        for val, rst in chain(
            map(lambda v: (v[0][1], v[1]),
                parse_record(rst, idnt)),
            map(lambda v: (v[0][0], v[1]),
                sequence(parse_value, optional(ignore_word("\n")))(rst)),
        ):
            for ((idnt_vls, vls), rst_vls) in parse_array(rst):
                if idnt == idnt_vls:
                    yield (idnt_vls, [val] + vls), rst_vls
                    return
            yield (idnt, [val]), rst
            return

def parse_record(src, delta = 0):
    for (ind, id), rst in sequence(
        parse_indent,
        parse_identifier,
        ignore_word(':'),
        ignore_spaces,
    )(src):
        
        ind += delta

        def sub_array(src):
            for _, src in ignore_word('\n')(src):
                for (ind_arr, arr), rst in parse_array(src):
                    if ind_arr > ind:
                        yield arr, rst
                return
        
        def sub_record(src):
            for _, rst in ignore_word('\n')(src):
                for (ind_sr, rec), rst in parse_record(rst):
                    if ind_sr > ind:
                        yield rec, rst
                    return
            
        def sub_value(src):
            for val, rst in parse_value(src):
                yield val, rst
                return
            
        for (val, rst) in chain(
            sub_record(rst),
            sub_array(rst),
            sub_value(rst),
        ):
            for _, rst in optional(ignore_word('\n'))(rst):
                for (ind_vls, vls), rst in parse_record(rst):
                    if ind_vls == ind:
                        yield (ind, {id: val, **vls}), rst
                        return
                yield (ind, {id: val}), rst
                return

def parse_identifier(src):
    word = ''
    last = 0
    for idx, c in enumerate(src):
        last = idx
        if c == '_' or (c >= 'a' and c <= 'z'):
            word += c
        else:
            break
    yield word, src[last:]

def ignore_spaces(src):
    for (idx, c) in enumerate(src):
        if c not in ' \t':
            yield None, src[idx:]
            return

def ignore_word(word):
    def ignore(src):
        if src.startswith(word):
            yield None, src[len(word):]
        return
    ignore.__name__ = f"ignore_{word}"
    return ignore

def parse_value(src):
    for val, rst in sequence(
                        ignore_word('"'),
                        parse_to_word('"'),
                        ignore_word('"'),
                        optional(ignore_spaces),
                        optional(ignore_word('\n')),
                    )(src):
        yield val[0], rst
        return
    for val, rst in sequence(
                        parse_to_word("\n"),
                        optional(ignore_word('\n')),
                    )(src):
        yield val[0].strip(), rst
        return

def parse_yaml(src):
    for val, rst in chain(
        parse_array(src),
        parse_record(src),
        parse_value(src),
    ):
        if isinstance(val, tuple):
            if val[0] != 0:
                return
            val = val[1]
        if rst.strip() == "":
            yield [val], ""
            return
        for vls, rst in parse_yaml(rst):
            if rst.strip() == "":
                yield [val] + vls, rst
                return
            

f = open("schedule.yaml", "r")
out = open ("result.json", "w")

for res in parse_yaml(f.read()):
    out.write(json.dumps(res[0][0], ensure_ascii=False))
    break


# out.write(json.dumps('', ensure_ascii=False§))

f.close()
out.close()
