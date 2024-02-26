from enum import Enum,auto

# debug tools
from pprint import pprint
import logging
import copy


logging.basicConfig(level=logging.DEBUG)


class Object_tag(Enum):
    """
    # Object tag
    """
    # 未定義
    UNDEF = auto()
    # 文字列
    STRING = auto()    # a-zA-Z
    # block
    SQBLOCK = auto()   # []
    PARENBLOCK = auto()# ()
    BLOCK = auto()     # {}
    # 式
    EXPR = auto()
    # 制御文法
    CONTROL = auto()
    # 単語
    WORD = auto()


class parser:
    # resolve <expr>
    # 式を解決します
    def __init__(self, code:str, mode = "lisp") -> None:
        self.code:str = code
        self.mode = mode

        # setting
        ## <, <=, >, >=, !=, <- (python で言うfor i in ...のin)
        self.rankinglist:dict = {
            # 演算子優先順位
            "&&":-1,"||":-1,

            "==":0,"!=":0,
            "<":0,">":0,
            "<=":0,">=":0,

            "+":1,"-":1,

            "*":2,"/":2,
            "%":2,"@":2,

            "^":3,"**":3
        }
        # TODO: 前置修飾(prefix)たとえば!(not)を解決する必要がある
        self.length_order_ope_list = sorted(self.rankinglist.keys(),key=lambda a:len(a))[::-1]
        self.blocks = [
            ('{','}',Block),
            ('[',']',ListBlock),
            ('(',')',ParenBlock),
        ]
        self.split = [' ', '\t','\n']
        self.word_excludes = [';',':',',']
        self.syntax_words = [
            "if",
            "elif",
            "else",
            "loop",
            "for",
            "while"
        ]
        # const
        self.ESCAPESTRING = "\\"

    # クォーテーションはまとまっている前提
    def resolve_quotation(self,code:str,quo_char:str) -> list[str]:
        # クォーテーションをまとめる
        open_flag:bool = False
        escape_flag:bool = False
        rlist:list = list()
        group:list = list()
        newline_counter :int = 0
        column_counter:int = 0
        for inner in code:
            if inner == "\n":
                column_counter = 0
                newline_counter += 1
            else:
                column_counter += 1

            if escape_flag:
                group.append(inner)
                escape_flag = False
            else:
                if inner == quo_char:
                    if open_flag:
                        group.append(inner)
                        rlist.append(
                            String(None,"".join(group))
                        )
                        group.clear()
                        open_flag = False
                    else:
                        group.append(inner)
                        position = (newline_counter,column_counter)
                        open_flag = True
                else:
                    if open_flag:
                        if inner == self.ESCAPESTRING:
                            escape_flag = True
                        else:
                            escape_flag = False
                        group.append(inner)
                    else:
                        rlist.append(inner)
        return rlist

    # grouping methods
    def grouping_elements(self,vec:list,open_char:str,close_char:str,ObjectInstance:"Elem") -> list:
        rlist:list[str] = list()
        group:list[str] = list()
        depth:int = 0

        for i in vec:
            if i == open_char:
                if depth > 0:
                    group.append(i)
                elif depth == 0:
                    pass
                else:
                    print("Error!")
                    return
                depth += 1
            elif i == close_char:
                depth -= 1
                if depth > 0:
                    group.append(i)
                elif depth == 0:
                    rlist.append(ObjectInstance(None,copy.copy(group)))
                    group.clear()
                else:
                    print("Error!")
                    return
            else:
                if depth > 0:
                    group.append(i)
                elif depth == 0:
                    rlist.append(i)
                else:
                    print("Error!")
                    return
        return rlist

    def grouping_words(self,vec:list,split:list[str],excludes:list[str]) -> list[str]:
        """
        # wordを切り出すメソッド
        
        - すでにElem に到達したらその時点で区切る
        - 区切り文字に到達したら区切る(/*例えば*/ 区切り文字: '\t', ' ', '\n')
        - 演算子に使用されている文字であれば区切る
        """
        rlist:list = list()
        group:list = list()
        ope_chars:str = ''.join(self.rankinglist.keys())
        ope_chars = ope_chars + ''.join(excludes)
        for i in vec:
            if isinstance(i,Elem):# Elemクラスを継承しているかどうか調べる
                # すでにrole決定済み
                if group:
                    rlist.append(Word(None,''.join(group)))
                    group.clear()
                rlist.append(i)
            elif i in split:
                # 区切り文字
                if group:
                    rlist.append(Word(None,''.join(group)))
                    group.clear()
            elif i in ope_chars:
                if group:
                    rlist.append(Word(None,''.join(group)))
                    group.clear()
                rlist.append(i)
            else:
                group.append(i) 
        if group:
            rlist.append(Word(None,''.join(group)))
            group.clear()
        return rlist
    
    def grouping_syntax(self,vec:list,syntax_words:list[str]) -> list:
        flag:bool = False
        group:list = list()
        rlist:list = list()
        for i in vec:
            if type(i) is Word:
                if i.get_contents() in syntax_words:
                    group.append(i)
                    flag = True
                else:
                    rlist.append(i)
            elif type(i) is ParenBlock:
                if flag:
                    group.append(i)
                else:
                    rlist.append(i)
            elif type(i) is Block:
                if flag:
                    group.append(i)
                    if len(group) == 2:
                        name: Word= group[0]
                        block: Block = group[1]
                        rlist.append(
                            Syntax(
                                name.get_contents(),
                                None,
                                block.get_contents()
                            )
                        )
                    elif len(group) == 3:
                        name:Word=group[0]
                        paren:ParenBlock = group[1]
                        block:Block = group[2]
                        rlist.append(
                            Syntax(
                                name.get_contents(),
                                paren.get_contents(),
                                block.get_contents()
                            )
                        )
                    else:
                        print("ここでError!",group)
                        return
                    group.clear()
                    flag = False
                else:
                    rlist.append(i)
            else:
                rlist.append(i)
        return rlist
    
    def grouping_function(self,vec:list) -> list:
        flag:bool = False
        name_tmp:Word = None
        rlist:list = list()
        for i in vec:
            if type(i) is Word:
                if flag:
                    rlist.append(name_tmp)
                name_tmp  = i
                flag = True
            elif type(i) is ParenBlock:
                if flag:
                    rlist.append(
                        Func(
                            name_tmp.get_contents(),# func name
                            i.get_contents(),       # args
                    ))
                    name_tmp = None
                    flag = False
                else:
                    rlist.append(i)
            else:
                if flag:
                    rlist.append(name_tmp)
                    rlist.append(i)
                    flag = False
                    name_tmp = None
                else:
                    rlist.append(i)
        if flag:
            rlist.append(name_tmp)
        return rlist

    def find_ope_from_list(self, text:str, ordered_opelist:list[str]) -> str:
        """
        演算子文字列が長い物から順に照会していって検索する
        # return
        str | None
        """
        for i in ordered_opelist:
            if text == i:
                return text
        return None

    def grouping_operator(self,vec:list,ordered_opelist:list[str]):
        """
        opeは長い順に並んでいる必要があります ex) ["<<<","<<","<"]
        """
        group:list = list()
        rlist:list = list()
        for i in vec:
            if not isinstance(i,Elem):
                # ここに来てもまだ、Elemインスタンスでない(すなわち、まだ未定の場合)
                group.append(i)
            else:
                if group:
                    ope =''.join(group) 
                    ope_text = self.find_ope_from_list(ope, ordered_opelist)
                    if ope_text is None:
                        rlist += group # concat
                    else:
                        rlist.append(Operator(ope))
                    group.clear()
                rlist.append(i)
        return rlist

    def is_number(self,text:str) -> bool:
        size = len(text)
        for i,j in enumerate(text):
            if i == 0 and j=='.':
                # ex) .141592
                return False
            if i == size - 1 and j=='.':
                # ex) 3.
                return False
            elif '0' <= j <= '9':
                pass
            else:
                return False
        return True

    def split_symbol(self,vec:list[str]) -> list[str]:
        pass

    def code2vec(self,code:str) ->list[str]:
        # クォーテーションをまとめる
        codelist = self.resolve_quotation(code, "\"")
        # ブロック、リストブロック、パレンブロック Elemをまとめる
        for i in self.blocks:codelist = self.grouping_elements(codelist, *i)
        # Wordをまとめる
        codelist = self.grouping_words(codelist, self.split, self.word_excludes)
        ## if, elif, else, forをまとめる
        codelist = self.grouping_syntax(codelist, self.syntax_words)
        ## functionの呼び出しをまとめる
        codelist = self.grouping_function(codelist)
        # TODO:もし配列モードであればここでカンマ区切りの処理をする
        # ここで初めて演算子をまとめる
        codelist = self.grouping_operator(codelist,self.length_order_ope_list)
        return codelist


# Base Elem
class Elem:
    """
    字句解析用データ型
    """
    def __init__(self, name:str, contents:str) -> None:
        self.name = name
        self.contents = contents

    def get_contents(self):return self.contents

    def get_name(self):return self.name
    
    def __repr__(self):return f"<{type(self).__name__} name:({self.name}) contents:({self.contents})>"


## Elements
class Block(Elem):
    """
    処理集合を格納
    <block> = {
        <proc>
    }
    <proc> = <expr> ;...
    # returns
    get_contents -> <proc>
    """
    def __init__(self, name: str, contents: str) -> None:super().__init__(name, contents)

class String(Elem):
    """
    文字列を格納
    "<string>"
    '<char>'
    # returns
    get_contents -> <string> or <char>
    """
    def __init__(self, name: str, contents: str) -> None:super().__init__(name, contents)

class ListBlock(Elem):
    """
    リストを格納
    [<expr>,...]
    # returns
    get_contents -> [<expr>,...] # 式集合
    """
    def __init__(self, name: str, contents: str) -> None:super().__init__(name, contents)

class ParenBlock(Elem):
    """
    式ブロック
    または
    関数の引数宣言部
    (<expr>,...)
    or
    (<dec>,...)
    <dec> = <word>:<type>
    # returns
    get_contents -> <expr>,... # 式集合 式の範囲で宣言集合になることはない
    """
    def __init__(self, name: str, contents: str) -> None:super().__init__(name, contents)

class Word(Elem):# Word Elemは仮どめ
    """
    引数、変数、関数定義、制御文法の文字列
    <word> = fn, let, const, if, while...(exclude: +, -, *, /)
    <word> = <syntax>, <name>, <type>, <Number>
    # returns
    get_contents -> <word>
    """
    def __init__(self, name: str, contents: str) -> None:super().__init__(name, contents)

class Syntax(Elem):
    """
    # returns
    <syntax> = if, elif, else, loop, for, while
    get_name ->  if, elif, else, loop, for, while
    get_expr -> <expr>
    get_contents -> {<proc>}
    """ 
    def __init__(self, name: str, expr, contents) -> None:
        super().__init__(name, contents)
        self.expr = expr

    def get_expr(self):
        return self.expr
    
    def __repr__(self):
        # override
        return f"<{type(self).__name__} name:({self.name}) expr:({self.expr}) contents:({self.contents})>"

class Func(Elem):
    """
    <name(excludes: 0-9)>(<expr>,...)
    # returns
    get_contents -> (srgs:[<expr>,...])
    get_name -> (funcname: <name>)
    """
    def __init__(self, name: str, contents: str) -> None:super().__init__(name, contents)

    def __repr__(self):
        return f"<{type(self).__name__} func name:({self.name}) args:({self.contents})>"

class Operator(Elem):
    """
    # returns
    get_contents -> ope(ope:["+","-","*","/",...])
    """

    def __init__(self, ope:str) -> None:
        super().__init__(None, ope)
        self.ope = ope

    def __repr__(self):
        return f"<{type(self).__name__} ope:({self.ope})>"


class Expr_parser(parser): # 式について解決します
    """
    # expressions resolver
    """
    def __init__(self, code: str, mode="lisp") -> None:
        super().__init__(code, mode)


class State_parser(parser): # 文について解決します
    """
    # statement resolver
    """
    def __init__(self, code: str, mode="lisp") -> None:
        super().__init__(code, mode)

# test

def __test_00():
    a = parser("")
    # expr test cases
    test_cases:list = list()
    with open("../examples/ex03.lc") as f :test_cases = [i for i in f]
    # print(test_cases)
    for testcase in test_cases:
        codelist = a.resolve_quotation(testcase,"\"")
        codelist = a.resolve_quotation(codelist,"'")
        for i in [
            ('{','}',Block),
            ('[',']',ListBlock),
            ('(',')',ParenBlock)]:
            codelist = a.grouping_elements(codelist,*i)
        print(testcase,codelist)
        print()

def __test_01():
    a = parser("")
    # expr test cases
    test_cases:list = list()
    with open("../examples/ex03.lc") as f :test_cases = [i for i in f]
    # print(test_cases)
    for testcase in test_cases:
        codelist = a.code2vec(testcase)
        pprint(codelist)
        print()

def __test_02():
    """
    # __test_04
    ## expr test

    
    """
    a = parser("")
    # expr test cases
    test_cases = [
"""
for (i <- list){
    const flag = string==i;
    if (if (flag){1} else {0}){
        const a = "hello" + "world";
        print("hello" + "world");
    };
}
""",
"""
loop {
    print("hello");
}
""",
    " 10 + ( x + log10(2) * sin(x) ) * log10(x)",
    "(-sin(x)*3)+(-2*cos(x))",
    "pi",
    "sin(x)",
    "(1)+2",
    "3.14",
    "-812+42",
    "a / b*(c+d)",
    "a / (b*(c+d))",
    "a*a*a",
    "x^3+x^2+3",
    "2*cube(x)+3*squared(x)+3",
    "10<=d<100"
    ]
    for testcase in test_cases:
        codelist = a.code2vec(testcase)
        print(testcase)
        pprint(codelist)
        print()


if __name__=="__main__":
    __test_02()
