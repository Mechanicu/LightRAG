from kconfiglib import (
    Symbol,
    Choice,
    MENU,
    COMMENT,
    MenuNode,
    BOOL,
    TRISTATE,
    STRING,
    INT,
    HEX,
    AND,
    OR,
    expr_str,
    expr_value,
    split_expr,
    standard_sc_expr_str,
    TRI_TO_STR,
    TYPE_TO_STR,
    standard_kconfig,
    standard_config_filename,
)


def _name_info(sc):
    # Returns a string with the name of the symbol/choice. Names are optional
    # for choices.

    return "Name: {}\n".format(sc.name) if sc.name else ""


def _prompt_info(sc):
    # Returns a string listing the prompts of 'sc' (Symbol or Choice)

    s = ""

    for node in sc.nodes:
        if node.prompt:
            s += "Prompt: {}\n".format(node.prompt[0])

    return s


def _value_info(sym):
    # Returns a string showing 'sym's value

    # Only put quotes around the value for string symbols
    return "Value: {}\n".format(
        '"{}"'.format(sym.str_value) if sym.orig_type == STRING else sym.str_value
    )


def _choice_syms_info(choice):
    # Returns a string listing the choice symbols in 'choice'. Adds
    # "(selected)" next to the selected one.

    s = "Choice symbols:\n"

    for sym in choice.syms:
        s += "  - " + sym.name
        if sym is choice.selection:
            s += " (selected)"
        s += "\n"

    return s + "\n"


def _help_info(sc):
    # Returns a string with the help text(s) of 'sc' (Symbol or Choice).
    # Symbols and choices defined in multiple locations can have multiple help
    # texts.

    s = "\n"

    for node in sc.nodes:
        if node.help is not None:
            s += "Help:\n\n{}\n\n".format(_indent(node.help, 2))

    return s


def _direct_dep_info(sc):
    # Returns a string describing the direct dependencies of 'sc' (Symbol or
    # Choice). The direct dependencies are the OR of the dependencies from each
    # definition location. The dependencies at each definition location come
    # from 'depends on' and dependencies inherited from parent items.

    return (
        ""
        if sc.direct_dep is _kconf.y
        else "Direct dependencies (={}):\n{}\n".format(
            TRI_TO_STR[expr_value(sc.direct_dep)], _split_expr_info(sc.direct_dep, 2)
        )
    )


def _defaults_info(sc):
    # Returns a string describing the defaults of 'sc' (Symbol or Choice)

    if not sc.defaults:
        return ""

    s = "Default"
    if len(sc.defaults) > 1:
        s += "s"
    s += ":\n"

    for val, cond in sc.orig_defaults:
        s += "  - "
        if isinstance(sc, Symbol):
            s += _expr_str(val)

            # Skip the tristate value hint if the expression is just a single
            # symbol. _expr_str() already shows its value as a string.
            #
            # This also avoids showing the tristate value for string/int/hex
            # defaults, which wouldn't make any sense.
            if isinstance(val, tuple):
                s += "  (={})".format(TRI_TO_STR[expr_value(val)])
        else:
            # Don't print the value next to the symbol name for choice
            # defaults, as it looks a bit confusing
            s += val.name
        s += "\n"

        if cond is not _kconf.y:
            s += "    Condition (={}):\n{}".format(
                TRI_TO_STR[expr_value(cond)], _split_expr_info(cond, 4)
            )

    return s + "\n"


def _split_expr_info(expr, indent):
    # Returns a string with 'expr' split into its top-level && or || operands,
    # with one operand per line, together with the operand's value. This is
    # usually enough to get something readable for long expressions. A fancier
    # recursive thingy would be possible too.
    #
    # indent:
    #   Number of leading spaces to add before the split expression.

    if len(split_expr(expr, AND)) > 1:
        split_op = AND
        op_str = "&&"
    else:
        split_op = OR
        op_str = "||"

    s = ""
    for i, term in enumerate(split_expr(expr, split_op)):
        s += "{}{} {}".format(indent * " ", "  " if i == 0 else op_str, _expr_str(term))

        # Don't bother showing the value hint if the expression is just a
        # single symbol. _expr_str() already shows its value.
        if isinstance(term, tuple):
            s += "  (={})".format(TRI_TO_STR[expr_value(term)])

        s += "\n"

    return s


def _select_imply_info(sym):
    # Returns a string with information about which symbols 'select' or 'imply'
    # 'sym'. The selecting/implying symbols are grouped according to which
    # value they select/imply 'sym' to (n/m/y).

    def sis(expr, val, title):
        # sis = selects/implies
        sis = [si for si in split_expr(expr, OR) if expr_value(si) == val]
        if not sis:
            return ""

        res = title
        for si in sis:
            res += "  - {}\n".format(split_expr(si, AND)[0].name)
        return res + "\n"

    s = ""

    if sym.rev_dep is not _kconf.n:
        s += sis(sym.rev_dep, 2, "Symbols currently y-selecting this symbol:\n")
        s += sis(sym.rev_dep, 1, "Symbols currently m-selecting this symbol:\n")
        s += sis(
            sym.rev_dep, 0, "Symbols currently n-selecting this symbol (no effect):\n"
        )

    if sym.weak_rev_dep is not _kconf.n:
        s += sis(sym.weak_rev_dep, 2, "Symbols currently y-implying this symbol:\n")
        s += sis(sym.weak_rev_dep, 1, "Symbols currently m-implying this symbol:\n")
        s += sis(
            sym.weak_rev_dep,
            0,
            "Symbols currently n-implying this symbol (no effect):\n",
        )

    return s


def _kconfig_def_info(item):
    # Returns a string with the definition of 'item' in Kconfig syntax,
    # together with the definition location(s) and their include and menu paths

    nodes = [item] if isinstance(item, MenuNode) else item.nodes

    s = "Kconfig definition{}, with parent deps. propagated to 'depends on'\n".format(
        "s" if len(nodes) > 1 else ""
    )
    s += (len(s) - 1) * "="

    for node in nodes:
        s += (
            "\n\n"
            "At {}:{}\n"
            "{}"
            "Menu path: {}\n\n"
            "{}".format(
                node.filename,
                node.linenr,
                _include_path_info(node),
                _menu_path_info(node),
                _indent(node.custom_str(_name_and_val_str), 2),
            )
        )

    return s


def _include_path_info(node):
    if not node.include_path:
        # In the top-level Kconfig file
        return ""

    return "Included via {}\n".format(
        " -> ".join(
            "{}:{}".format(filename, linenr) for filename, linenr in node.include_path
        )
    )


def _menu_path_info(node):
    # Returns a string describing the menu path leading up to 'node'

    path = ""

    while node.parent is not _kconf.top_node:
        node = node.parent

        # Promptless choices might appear among the parents. Use
        # standard_sc_expr_str() for them, so that they show up as
        # '<choice (name if any)>'.
        path = (
            " -> "
            + (node.prompt[0] if node.prompt else standard_sc_expr_str(node.item))
            + path
        )

    return "(Top)" + path


def _indent(s, n):
    # Returns 's' with each line indented 'n' spaces. textwrap.indent() is not
    # available in Python 2 (it's 3.3+).

    return "\n".join(n * " " + line for line in s.split("\n"))


def _name_and_val_str(sc):
    # Custom symbol/choice printer that shows symbol values after symbols

    # Show the values of non-constant (non-quoted) symbols that don't look like
    # numbers. Things like 123 are actually symbol references, and only work as
    # expected due to undefined symbols getting their name as their value.
    # Showing the symbol value for those isn't helpful though.
    if isinstance(sc, Symbol) and not sc.is_constant and not _is_num(sc.name):
        if not sc.nodes:
            # Undefined symbol reference
            return "{}(undefined/n)".format(sc.name)

        return "{}(={})".format(sc.name, sc.str_value)

    # For other items, use the standard format
    return standard_sc_expr_str(sc)


def _expr_str(expr):
    # Custom expression printer that shows symbol values
    return expr_str(expr, _name_and_val_str)

def _is_num(name):
    # Heuristic to see if a symbol name looks like a number, for nicer output
    # when printing expressions. Things like 16 are actually symbol names, only
    # they get their name as their value when the symbol is undefined.

    try:
        int(name)
    except ValueError:
        if not name.startswith(("0x", "0X")):
            return False

        try:
            int(name, 16)
        except ValueError:
            return False

    return True

def _info_str(node):
    # Returns information about the menu node 'node' as a string.
    #
    # The helper functions are responsible for adding newlines. This allows
    # them to return "" if they don't want to add any output.

    if isinstance(node.item, Symbol):
        sym = node.item

        return (
            _name_info(sym)
            + _prompt_info(sym)
            + "Type: {}\n".format(TYPE_TO_STR[sym.type])
            + _value_info(sym)
            + _help_info(sym)
            + _direct_dep_info(sym)
            + _defaults_info(sym)
            + _select_imply_info(sym)
            + _kconfig_def_info(sym)
        )

    if isinstance(node.item, Choice):
        choice = node.item

        return (
            _name_info(choice)
            + _prompt_info(choice)
            + "Type: {}\n".format(TYPE_TO_STR[choice.type])
            + "Mode: {}\n".format(choice.str_value)
            + _help_info(choice)
            + _choice_syms_info(choice)
            + _direct_dep_info(choice)
            + _defaults_info(choice)
            + _kconfig_def_info(choice)
        )
    return _kconfig_def_info(node)  # node.item in (MENU, COMMENT)


def _parent_menu(node):
    # Returns the menu node of the menu that contains 'node'. In addition to
    # proper 'menu's, this might also be a 'menuconfig' symbol or a 'choice'.
    # "Menu" here means a menu in the interface.

    menu = node.parent
    while not menu.is_menuconfig:
        menu = menu.parent
    return menu


def _shown_nodes(menu, show_type):
    # Returns the list of menu nodes from 'menu' (see _parent_menu()) that
    # would be shown when entering it

    def rec(node):
        res = []

        while node:
            if _visible(node) or show_type:
                res.append(node)
                if node.list and not node.is_menuconfig:
                    # Nodes from implicit menu created from dependencies. Will
                    # be shown indented. Note that is_menuconfig is True for
                    # menus and choices as well as 'menuconfig' symbols.
                    res += rec(node.list)

            elif node.list and isinstance(node.item, Symbol):
                # Show invisible symbols if they have visible children. This
                # can happen for an m/y-valued symbol with an optional prompt
                # ('prompt "foo" is COND') that is currently disabled. Note
                # that it applies to both 'config' and 'menuconfig' symbols.
                shown_children = rec(node.list)
                if shown_children:
                    res.append(node)
                    if not node.is_menuconfig:
                        res += shown_children

            node = node.next

        return res

    if isinstance(menu.item, Choice):
        # For named choices defined in multiple locations, entering the choice
        # at a particular menu node would normally only show the choice symbols
        # defined there (because that's what the MenuNode tree looks like).
        #
        # That might look confusing, and makes extending choices by defining
        # them in multiple locations less useful. Instead, gather all the child
        # menu nodes for all the choices whenever a choice is entered. That
        # makes all choice symbols visible at all locations.
        #
        # Choices can contain non-symbol items (people do all sorts of weird
        # stuff with them), hence the generality here. We really need to
        # preserve the menu tree at each choice location.
        #
        # Note: Named choices are pretty broken in the C tools, and this is
        # super obscure, so you probably won't find much that relies on this.
        # This whole 'if' could be deleted if you don't care about defining
        # choices in multiple locations to add symbols (which will still work,
        # just with things being displayed in a way that might be unexpected).

        # Do some additional work to avoid listing choice symbols twice if all
        # or part of the choice is copied in multiple locations (e.g. by
        # including some Kconfig file multiple times). We give the prompts at
        # the current location precedence.
        seen_syms = {
            node.item for node in rec(menu.list) if isinstance(node.item, Symbol)
        }
        res = []
        for choice_node in menu.item.nodes:
            for node in rec(choice_node.list):
                # 'choice_node is menu' checks if we're dealing with the
                # current location
                if node.item not in seen_syms or choice_node is menu:
                    res.append(node)
                    if isinstance(node.item, Symbol):
                        seen_syms.add(node.item)
        return res

    return rec(menu.list)


def _visible(node):
    # Returns True if the node should appear in the menu (outside show-all
    # mode)

    return (
        node.prompt
        and expr_value(node.prompt[1])
        and not (node.item == MENU and not expr_value(node.visibility))
    )


class KconfiglibHelper:
    def __init__(self):
        self.kconf = standard_kconfig(__doc__)
        global _kconf
        _kconf = self.kconf
        # current MenuNode, start from top
        self.cur_menu = self.kconf.top_node
        # ignore visibility and show all option, default to false
        self.is_show_all = False
        # MenuNode itself info stored in list
        self.self_node_idx_inlist = 0
        # visible sub option list header of current MenuNode
        self.cur_vis_lh = _shown_nodes(self.cur_menu, self.is_show_all)

    def get_target_node_all_info(self, node):
        # Get lines of help text
        lines = _info_str(node).split("\n")
        return lines

    def get_cur_node_info(self):
        return self.get_target_node_all_info(
            self.cur_vis_lh[self.self_node_idx_inlist]
        )

    def get_cur_vis_list_info(self):
        infos = []
        for node in self.cur_vis_lh:
            infos.append(self.get_target_node_all_info(node))
        return infos
