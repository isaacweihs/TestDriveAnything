from enum import Enum
from itertools import islice
from re import findall

def parse_blk_to_dict(data: str, start: int = 0) -> (dict, int):
    """
    Parses a string with the format of a .blk file into a sort of tuple.

    Args:
        start (int): character to start from. Defaults to 0
        data (str, optional): data to parse.

    Raises:
        SyntaxError: Unexpected character
        SyntaxError: Invalid matrix format
        ValueError: Unknown type
        ValueError: Unknown boolean value
        ValueError: Expected `a` values, got `b` 
        SyntaxError: Unknown state

    Returns:
        tuple, int: Resulting list of tuple(s), length of list
    """
    class States(Enum):
        ID_NEXT = 1
        ID = 2
        BLOCK_NEXT = 3
        TYPE_NEXT = 4
        TYPE = 5
        EQUALS_NEXT = 6
        VALUE_NEXT = 7
        VALUE = 8
        STRING = 9

    def unexpected():
        raise SyntaxError(f'Unexpected character #{i}: {ch}')

    def matrix(m: str) -> list | float:
        m = m.strip()

        if not m.startswith('[') or not m.endswith(']'):
            xs = m.split(',')
            if len(xs) > 1:
                return [matrix(v) for v in xs]
            try:
                v = float(m)
                return v
            except ValueError:
                raise SyntaxError(f'Invalid matrix format {s}')

        m = m[1:-1]
        return [matrix(v) for v in findall(r'\[([^]]+)]', m)]

    state = States.ID_NEXT
    s = ''
    _id = ''
    _type = ''
    result = []
    enum_data = iter(enumerate(data))
    next(islice(enum_data, start, start), None)
    for i, ch in enum_data:
        match state:
            case States.ID_NEXT:
                if ch.isalnum() or ch in ['_', '.']:
                    s = ch
                    state = States.ID
                elif ch.isspace():
                    pass
                elif ch == '}':
                    return result, i + 1
                else:
                    unexpected()
            case States.ID:
                if ch == ':':
                    _id = s
                    state = States.TYPE_NEXT
                elif ch.isspace():
                    _id = s
                    state = States.BLOCK_NEXT
                elif ch.isalnum() or ch in ['_', '.']:
                    s += ch
                elif ch == '{':
                    _id = s
                    sub_result, n = parse_blk_to_dict(data, i + 1)
                    result.append((_id, sub_result))
                    next(islice(enum_data, n - i - 1, n - i - 1), None)
                    state = States.ID_NEXT
                else:
                    unexpected()
            case States.BLOCK_NEXT:
                if ch == '{':
                    sub_result, n = parse_blk_to_dict(data, i + 1)
                    result.append((_id, sub_result))
                    next(islice(enum_data, n - i - 1, n - i - 1), None)
                    state = States.ID_NEXT
                elif ch.isspace():
                    pass
                else:
                    unexpected()
            case States.TYPE_NEXT:
                if ch.isalpha():
                    s = ch
                    state = States.TYPE
                elif ch.isspace():
                    pass
                else:
                    unexpected()
            case States.TYPE:
                if ch.isalnum():
                    s += ch
                elif ch == '=':
                    _type = s
                    if _type not in ['i', 'r', 't', 'b', 'm', 'p2', 'p3', 'p4']:
                        raise ValueError(f'Unknown type {_type}')
                    state = States.VALUE_NEXT
                elif ch.isspace():
                    _type = s
                    state = States.EQUALS_NEXT
                else:
                    unexpected()
            case States.EQUALS_NEXT:
                if ch == '=':
                    state = States.VALUE_NEXT
                elif ch.isspace():
                    pass
                else:
                    unexpected()
            case States.VALUE_NEXT:
                if ch == '"':
                    s = ''
                    state = States.STRING
                elif ch.isalnum() or ch in '[+-':
                    s = ch
                    state = States.VALUE
                elif ch.isspace():
                    pass
                else:
                    unexpected()
            case States.STRING:
                if ch == '"':
                    state = States.ID_NEXT
                    result.append((_id, s))
                else:
                    s += ch
            case States.VALUE:
                if ch in [';', '\n', '"']:
                    state = States.ID_NEXT
                    value = s
                    match _type:
                        case 'i':
                            value = int(s)
                        case 'r':
                            value = float(s)
                        case 't':
                            value = s
                        case 'b':
                            if s not in ['yes', 'true', 'no', 'false']:
                                raise ValueError(f'Unknown boolean value {s}')
                            value = s in ['yes', 'true']
                        case 'm':
                            value = matrix(s)
                        case 'p2' | 'p3' | 'p4':
                            value = tuple(float(v) for v in s.split(','))
                            if (r := len(value)) != (e := int(_type[1])):
                                raise ValueError(f'Expected {e} values, got {r}')
                    result.append((_id, value))
                elif ch.isalnum() or ch.isspace() or ch in '_/"[].,+-':
                    s += ch
                elif ch == '}':
                    result.append((_id, s))
                    return result, i + 1
                else:
                    unexpected()
            case _:
                raise SyntaxError(f'Unknown state {state}')
    return result, len(data)


def parse_dict_to_blk(data, indent: int = 0) -> str:
    """
    Parses a list of tuples into a .blk-formatted string

    Args:
        data: Data to parse
        indent (int, optional): Default indentation. Defaults to 0.

    Returns:
        str: parsed string
    """
    def serialize_value(value):
        if isinstance(value, bool):
            return f'b={"yes" if value else "no"}'
        elif isinstance(value, float):
            return f'r={int(value)}' if value.is_integer() else f'r={value}'
        elif isinstance(value, str):
            return f't="{value}"'
        elif isinstance(value, int):
            return f'i={value}'
        elif isinstance(value, tuple):
            return f'p{len(value)}={",".join(str(int(i)) if isinstance(i, float) and i.is_integer() else str(i) for i in value)}'
        elif isinstance(value, list):
            if all(isinstance(i, dict) for i in value):
                return value  # Handle list of dicts in serialize_dict
            elif all(isinstance(i, float) for i in value):
                return f'm=[{",".join(str(int(i)) if i.is_integer() else str(i) for i in value)}]'
            elif all(isinstance(i, list) and all(isinstance(j, float) or isinstance(j, int) for j in i) for i in value):
                return f'm=[{" ".join(f"[{",".join(str(int(j)) if isinstance(j, float) and j.is_integer() else str(j) for j in i)}]" for i in value)}]'
            else:
                return [serialize_value(item) for item in value]
        elif isinstance(value, list) and all(isinstance(i, tuple) and len(i) == 2 for i in value):
            return serialize_dict(value, indent + 1)
        elif isinstance(value, dict):
            return serialize_dict(value, 1)  # Serialize nested dictionary
        else:
            raise ValueError(f'Unknown type {type(value)} for value {value}')

    def serialize_dict(d, level):
        indent_str = ' ' * (level * 2)
        lines = []
        for key, value in d:
            if isinstance(value, list) and all(isinstance(i, tuple) and len(i) == 2 for i in value):
                lines.append(f'{indent_str}{key}{{')
                lines.append(serialize_dict(value, level + 1))
                lines.append(f'{indent_str}}}')
            elif isinstance(value, dict):
                lines.append(f'{indent_str}{key}{{')
                lines.append(serialize_dict(value.items(), level + 1))
                lines.append(f'{indent_str}}}')
            else:
                lines.append(f'{indent_str}{key}:{serialize_value(value)}')
        return '\n'.join(lines)

    return serialize_dict(data, indent)

def find_element_by_path(data, path):
    """
    Access elements in a nested list of tuples structure by specifying a path.

    Args:
        data: The list of tuples representing the parsed .blk data.
        path: A list of keys and/or indices representing the path to the desired element.

    Returns:
        The element (key, value) at the specified path or None if not found.
    """
    for key in path:
        if isinstance(key, int):
            if isinstance(data, list) and 0 <= key < len(data):
                data = data[key]
            else:
                return None
        else:
            found = False
            for k, v in data:
                if k == key:
                    if isinstance(v, list) and all(isinstance(i, tuple) for i in v):
                        data = v
                        found = True
                        break
                    else:
                        return k
            if not found:
                return None
    return data

def find_element_by_value(data, target_value, parent=None, path=None, path_is_index=False):
    """
    Recursively searches for a target value in a nested list of tuples structure.

    Args:
        data: The list of tuples representing the parsed .blk data.
        target_value: The value to search for.
        parent: The parent key to restrict the search to (optional).
        path: The current path (used for recursion).
        path_is_index: Whether to return the path with index specifiers.
    
    Returns:
        The path to the target element if found, None otherwise.
    """
    if path is None:
        path = []

    if isinstance(data, list):
        for idx, element in enumerate(data):
            if not isinstance(element, tuple) or len(element) != 2:
                continue  # Skip elements that are not valid (key, value) pairs

            key, value = element
            new_path = path + [idx if path_is_index else key]
            if parent and key == parent:
                if isinstance(value, list):
                    for sub_idx, sub_element in enumerate(value):
                        if not isinstance(sub_element, tuple) or len(sub_element) != 2:
                            continue  # Skip elements that are not valid (key, value) pairs

                        sub_key, sub_value = sub_element
                        if sub_value == target_value:
                            return new_path + [sub_idx if path_is_index else sub_key]
                        elif isinstance(sub_value, list):
                            result = find_element_by_value(sub_value, target_value, parent=None, path=new_path + [sub_idx if path_is_index else sub_key], path_is_index=path_is_index)
                            if result:
                                return result
            elif not parent and value == target_value:
                return new_path
            elif isinstance(value, list):
                result = find_element_by_value(value, target_value, parent=parent, path=new_path, path_is_index=path_is_index)
                if result:
                    return result

    return None

def find_value_by_path(data, path):
    """
    Find the value of the element specified by the path.

    Args:
        data: The list of tuples representing the parsed .blk data.
        path: A list of keys and/or indices representing the path to the desired element.

    Returns:
        The value at the specified path or None if not found.
    """
    for key in path:
        if isinstance(key, int):  # Use index to specify element.
            if isinstance(data, list) and 0 <= key < len(data):
                data = data[key][1]
            else:
                return None
        else:
            found = False
            for k, v in data:
                if k == key:
                    data = v
                    found = True
                    break
            if not found:
                return None
    return data

def find_value_by_element(data, target_element, parent=None):
    """
    Find the value of the first matching element. If parent is specified, return the value of the first matching element with a matching parent.

    Args:
        data: The list of tuples representing the parsed .blk data.
        target_element: The element to search for.
        parent: The parent key or path to restrict the search to (optional).

    Returns:
        The value of the first matching element or None if not found.
    """
    def recursive_search(data, target_element, parent, found_parent):
        if isinstance(data, list):
            for idx, element in enumerate(data):
                if not isinstance(element, tuple) or len(element) != 2:
                    continue  # Skip elements that are not valid (key, value) pairs

                key, value = element
                current_path = parent if isinstance(parent, list) else []
                
                if isinstance(parent, str) and key == parent:
                    found_parent = True
                elif isinstance(parent, list) and current_path and (key == current_path[0] or idx == current_path[0]):
                    if len(current_path) == 1:
                        found_parent = True
                    else:
                        new_parent_path = current_path[1:]
                        if isinstance(value, list):
                            result = recursive_search(value, target_element, new_parent_path, found_parent)
                            if result is not None:
                                return result
                        continue

                if key == target_element and (not parent or found_parent):
                    return value
                if isinstance(value, list):
                    result = recursive_search(value, target_element, parent, found_parent)
                    if result is not None:
                        return result
        return None

    return recursive_search(data, target_element, parent, False)

def modify_value_by_path(data, path, new_value):
    """
    Modify elements in a nested list of tuples structure by specifying a path and new value.
    
    Args:
        data: The list of tuples representing the parsed .blk data.
        path: A list of keys and/or indices representing the path to the desired element.
        new_value: The new value to set at the specified path.
        
    Returns:
        The modified data structure with the new value set at the specified path.
    """
    if not path:
        return data

    *sub_path, final_key = path

    target = data
    for key in sub_path:
        if isinstance(key, int):
            if isinstance(target, list) and 0 <= key < len(target):
                target = target[key][1]
            else:
                return data
        else:
            found = False
            for k, v in target:
                if k == key:
                    if isinstance(v, list) and all(isinstance(i, tuple) for i in v):
                        target = v
                        found = True
                        break
                    else:
                        target = v
                        found = True
                        break
            if not found:
                return data

    if isinstance(final_key, int):
        if isinstance(target, list) and 0 <= final_key < len(target):
            target[final_key] = (target[final_key][0], new_value)
    else:
        for idx, (k, v) in enumerate(target):
            if k == final_key:
                target[idx] = (k, new_value)
                break

    return data

def closest_parent(data, element):
    """
    Find the closest parent of a given element in a nested list of tuples structure.

    Args:
        data: The list of tuples representing the parsed .blk data.
        element: The element to search for.

    Returns:
        The key of the closest parent or None if not found.
    """
    def recursive_search(data, element, current_parent=None):
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, tuple) or len(item) != 2:
                    continue  # Skip elements that are not valid (key, value) pairs

                key, value = item
                if key == element:
                    return current_parent

                if isinstance(value, list):
                    result = recursive_search(value, element, key)
                    if result is not None:
                        return result
        return None

    return recursive_search(data, element)

def closest_parent_by_path(data, path):
    """
    Find the closest parent of a given element specified by a path in a nested list of tuples structure.

    Args:
        data: The list of tuples representing the parsed .blk data.
        path: A list of keys and/or indices representing the path to the desired element.

    Returns:
        The path to the closest parent element or None if not found.
    """
    if not path:
        return None
    
    *parent_path, _ = path

    if not parent_path:
        return None

    for key in parent_path:
        if isinstance(key, int):
            if isinstance(data, list) and 0 <= key < len(data):
                data = data[key][1]
            else:
                return None
        else:
            found = False
            for k, v in data:
                if k == key:
                    if isinstance(v, list) and all(isinstance(i, tuple) for i in v):
                        data = v
                        found = True
                        break
                    else:
                        return k
            if not found:
                return None
    return parent_path

def path_of_element(data, element, path_is_index=False):
    """
    Find the path of a given element in a nested list of tuples structure.

    Args:
        data: The list of tuples representing the parsed .blk data.
        element: The element to search for.
        path_is_index: Whether to return the path as integer indices.

    Returns:
        The path to the element as a list of keys or indices, or None if not found.
    """
    def recursive_search(data, element, current_path):
        if isinstance(data, list):
            for idx, item in enumerate(data):
                if not isinstance(item, tuple) or len(item) != 2:
                    continue  # Skip elements that are not valid (key, value) pairs

                key, value = item
                new_path = current_path + [idx if path_is_index else key]

                if key == element:
                    return new_path

                if isinstance(value, list):
                    result = recursive_search(value, element, new_path)
                    if result is not None:
                        return result
        return None

    return recursive_search(data, element, [])