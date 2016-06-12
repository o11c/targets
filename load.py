#!/usr/bin/env python3
import collections
import os
import re
import types
import yaml

class OrderedUniqueSafeLoader(yaml.SafeLoader):
    # hide the possible-filled dicts from base classes
    yaml_constructors = {}
    yaml_multi_constructors = {}

    forbid_duplicates = True

    def construct_mapping(self, node, deep=False):
        if isinstance(node, yaml.MappingNode):
            self.flatten_mapping(node)
        if not isinstance(node, yaml.MappingNode):
            raise yaml.constructor.ConstructorError(None, None,
                    "expected a mapping node, but found %s" % node.id,
                    node.start_mark)
        mapping = collections.OrderedDict()
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, collections.Hashable):
                raise yaml.constructor.ConstructorError("while constructing a mapping", node.start_mark,
                        "found unhashable key", key_node.start_mark)
            value = self.construct_object(value_node, deep=deep)
            if self.forbid_duplicates and key in mapping:
                raise yaml.constructor.ConstructorError("while constructing a mapping", node.start_mark,
                        "found duplicate key", key_node.start_mark)
            mapping[key] = value
        return mapping


class YamlCacher:
    def __init__(self):
        self._cache = {}

    def _load_stream(self, stream):
        rv = yaml.load(stream, OrderedUniqueSafeLoader)
        if rv is None:
            rv = collections.OrderedDict()
        return rv

    def load_file(self, name):
        try:
            return self._cache[name]
        except KeyError:
            pass
        with open(name) as f:
            rv = self._load_stream(f)
        self._cache[name] = rv
        return rv

class Merger:
    def __init__(self, cacher, name):
        self._cacher = cacher
        self._merged_dict = collections.OrderedDict()
        self._name = os.path.basename(name)
        # Invariant: these are disjoint, see logic at end of _load().
        self._done = set()
        self._blacklist = []

    def _optional_unique_check(self, key, val, old_val):
        assert old_val is None
        if val is None:
            return ''
        assert isinstance(val, str)
        return val

    def _simple_unique_check(self, key, val, old_val):
        assert old_val is None, '%r not unique for %s' % (key, self._name)
        assert val is not None, '%r not defined for %s' % (key, self._name)
        assert isinstance(val, str)
        return val

    def _simple_override_check(self, key, val, old_val):
        assert val is not None, '%r not defined for %s' % (key, self._name)
        assert isinstance(val, str)
        return val

    def check_triples(self, key, val, old_val):
        assert old_val is None
        assert isinstance(val, list)
        assert val[0] == self._name, 'Mismatch triple %r in file %r' % (val[0], self._name)
        assert len(self._blacklist) == 1, 'triple must be in top file'
        assert 'triple/%s' % self._name == self._blacklist[-1]
        val_set = set(val)
        assert len(val_set) == len(val), 'Duplicate aliases in %s' % self._name
        # TODO check or make symlinks?
        return val

    # `variants` is optional, but if it is defined,
    # then `variant_flags` must also be defined and not empty
    def check_variants(self, key, val, old_val):
        if val is None:
            return []
        assert old_val is None
        assert isinstance(val, list)
        val_set = set(val)
        assert len(val_set) == len(val)
        assert self._name not in val_set, self._name
        for other in val:
            assert os.path.exists('triple/%s.yml' % other), other
        return val

    check_variant_flags = _optional_unique_check
    check_arch = _simple_override_check
    check_kernel = _simple_override_check

    def check_endian(self, key, val, old_val):
        assert val is not None, '%r not defined' % key
        assert val in {'little', 'big'} # PDP and Honeywell not supported.
        return val

    def check_cpp(self, key, val, old_val):
        # TODO: normalize all values, particularly:
        # * remove duplicates
        # * convert FOO to defined FOO  when it is alone or negated, but
        #   leave FOO == BAR and FOO == val as-is. Except it *also* needs
        #   to *add* defined= statements to both.
        # TODO: do I even need explicit !s, if I generate them *all* ?
        assert isinstance(val, list), type(val)
        val_set = set(val)
        for v in val:
            # TODO: The only || right now is for cygwin ...
            assert re.fullmatch('![A-Za-z_][A-Za-z_0-9]*|[A-Za-z_][A-Za-z_0-9]*( (==|\|\|) [A-Za-z_0-9]+)?', v), v
        if old_val is not None:
            old_val.extend(val)
        else:
            old_val = val
        return old_val

    def check_cpp_require(self, key, val, old_val):
        if val is None:
            return []
        assert isinstance(val, list), type(val)
        if old_val is not None:
            old_val.extend(val)
        else:
            old_val = val
        return old_val

    check_libc = _simple_override_check
    check_default_char_sign = _simple_override_check
    check_short = _simple_override_check
    check_int = _simple_override_check
    check_long = _simple_override_check
    check_long_long = _simple_override_check
    check_size = _simple_override_check
    check_ptr = _simple_override_check
    check_reg = _simple_override_check
    check_obj = _simple_override_check

    # TODO figure out how to handle bare stuff like i386-elf

    def verify(self):
        # TODO if anything is missing, be incomplete?
        for attr in sorted(dir(self)):
            if not attr.startswith('check_'):
                continue
            key = attr[len('check_'):]
            if key not in self._merged_dict:
                fun = getattr(self, attr)
                assert isinstance(fun, types.MethodType)
                val = None
                self._merged_dict[key] = fun(key, val, None)
        assert bool(self._merged_dict['variants']) == bool(self._merged_dict['variant_flags']), self._name

    def _load(self, name):
        # TODO cache imported files that are shared between multiple triples.
        # (should they be Merger objects too? with an 'incomplete' bool?)
        if name in self._done:
            return
        assert '.' not in name
        assert name not in self._blacklist
        self._blacklist.append(name)

        fn = name + '.yml'
        od = self._cacher.load_file(fn)
        assert isinstance(od, collections.OrderedDict), (fn, type(od).__name__)
        for key, val in od.items():
            if key == 'import':
                assert isinstance(val, list)
                for fn2 in val:
                    assert isinstance(fn2, str)
                    self._load(fn2)
                continue
            attr = 'check_' + key
            fun = getattr(self, attr, None)
            if fun is None:
                raise KeyError('Invalid key %r in %r' % (key, fn))
            assert isinstance(fun, types.MethodType)
            val = fun(key, val, self._merged_dict.get(key))
            self._merged_dict[key] = val
        self._blacklist.pop()
        self._done.add(name)

def load(cacher, name):
    if name.endswith('.yml'):
        name = name[:-len('.yml')]
    rv = Merger(cacher, name)
    rv._load('misc/default')
    rv._load(name)
    rv.verify()
    return rv

def main():
    import sys

    assert len(sys.argv) > 1
    cacher = YamlCacher()
    for name in sys.argv[1:]:
        assert not name.startswith('-')
        load(cacher, name)

if __name__ == '__main__':
    main()
