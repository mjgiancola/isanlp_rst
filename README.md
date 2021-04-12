![Python 3.7](https://img.shields.io/badge/python-3.7-green.svg)

# IsaNLP RST Parser
This Python 3 library provides RST parser for Russian based on neural network models trained on [RuRSTreebank](https://rstreebank.ru/) Russian discourse corpus. The parser should be used in conjunction with [IsaNLP library](https://github.com/IINemo/isanlp) and can be considered its module.  

## Installation

1. Install IsaNLP and its dependencies:
```
pip install grpcio
pip install git+https://github.com/IINemo/isanlp.git
```  

2. Deploy docker containers for syntax and discourse parsing:  
```
docker run --rm -p 3334:3333 inemo/isanlp_udpipe
docker run --rm -p 3335:3333 tchewik/isanlp_rst
```  
3. Connect from python using `PipelineCommon`:  
```python  
#
from isanlp import PipelineCommon
from isanlp.processor_remote import ProcessorRemote
from isanlp.ru.processor_mystem import ProcessorMystem
from isanlp.ru.converter_mystem_to_ud import ConverterMystemToUd 
#
ppl = PipelineCommon([
    (ProcessorRemote('localhost', 3334, '0'),
     ['text'],
     {'sentences': 'sentences',
      'tokens': 'tokens',
      'lemma': 'lemma',
      'syntax_dep_tree': 'syntax_dep_tree',
      'postag': 'ud_postag'}),
    (ProcessorMystem(delay_init=False),
     ['tokens', 'sentences'],
     {'postag': 'postag'}),
    (ConverterMystemToUd(),
     ['postag'],
     {'morph': 'morph',
      'postag': 'postag'}),
    (ProcessorRemote('localhost', 3335, 'default'),
     ['text', 'tokens', 'sentences', 'postag', 'morph', 'lemma', 'syntax_dep_tree'],
     {'rst': 'rst'})
])

text = (
"Новости о грядущей эмиссии в США обвалили доллар и подняли цену золота. При этом рост количества "
"долларов пока не зафиксирован. Со швейцарским франком ситуация противоположная: стало известно, ч"
"то в феврале денежная масса Швейцарии увеличилась на 3.5%, однако биржевой курс франка и его покуп"
"ательная способность за неделю выросли."
)

res = ppl(text)
#
```   
4. The `res` variable should contain all annotations including RST annotations stored in `res['rst']`; each tree anotation in list represents one or more paragraphs of the given text.

```
{'text': 'Новости о грядущей эмиссии ...',
 'sentences': [<isanlp.annotation.Sentence at 0x7f833dee07d0>, ...],
 'tokens': [<isanlp.annotation.Token at 0x7f833dee0910>, ...],
 'lemma': [['новость', ...], ...],
 'syntax_dep_tree': [[<isanlp.annotation.WordSynt at 0x7f833deddc10>, ...], ...],
 'ud_postag': [['NOUN', ...], ...],
 'postag': [['NOUN', ...], ...],
 'morph': [[{'fPOS': 'NOUN', 'Gender': 'Fem', ...}, ...], ...],
 'rst': [<isanlp.annotation_rst.DiscourseUnit at 0x7f833defa5d0>]}
```

5. The variable `res['rst']` can be visualized as:  
<img src="examples/example.rs3.png" width="700">

6. To convert DiscourseUnit objects to .rs3 file with visualization, run:

```python

res['rst'][0].to_rs3('first_tree_filename.rs3')
```

7. To convert all DiscourseUnits in a document as a single .rs3 file with multiple trees, run:

```python

from isanlp.annotation_rst import ForestExporter
exporter = ForestExporter(encoding='utf8')
exporter(res['rst'], 'filename.rs3')
```
It is recommended to open the generated .rs3 files with [RSTTool](http://www.wagsoft.com/RSTTool/).

## Package overview  
1. The discourse parser. Is implemented in `ProcessorRST` class. Path: `src/isanlp_rst/processor_rst.py`.
2. Trained neural network models for RST parser: models for segmentation, structure prediction, and label prediction. Path: `models`.
3. Docker container [tchewik/isanlp_rst](https://hub.docker.com/r/tchewik/isanlp_rst/) that contains preinstalled libraries and models. The container provides gRPC service for RST parsing. The container can be obtained with the command:  
`docker run --rm -p 3335:3333 tchewik/isanlp_rst`

## Usage 

The usage example is available in `examples/usage.ipynb`.

### RST data structures
The results of RST parser are stored in a list of `isanlp.annotation_rst.DiscourseUnit` objects. Each object represents a tree for a paragraph or multiple paragraphs of a text.
DiscourseUnit objects have the following members:
  * id(int): id of a discourse unit.
  * start(int): starting position (in characters) of a current discourse unit span in original text.
  * end(int): ending position (in characters) of a current discourse unit span in original text.
  * relation(string): 'elementary' if the current unit is a discourse tree leaf, or RST relation.
  * nuclearity(string): nuclearity orientation for current unit. `_` for elementary discourse units or one of `NS`, `SN`, `NN` for non-elementary units.
  * left(DiscourseUnit or None): left child node of a non-elementary unit.
  * right(DiscourseUnit or None): right child node of a non-elementary unit.
  * proba(float): probability of the node presence obtained from structure classifier.

It is possible to operate with DiscourseUnits objects as binary structures. For example, to extract relations pairs from the tree like this:
```python
def extr_pairs(tree, text):
    pp = []
    if tree.left:
        pp.append([text[tree.left.start:tree.left.end],
                   text[tree.right.start:tree.right.end], 
                   tree.relation, tree.nuclearity])
        pp += extr_pairs(tree.left, text)
        pp += extr_pairs(tree.right, text)
    return pp
    
print(extr_pairs(res['rst'][0], res['text']))
```  

The result for `'Президент Филиппин заявил, что поедет на дачу, если будут беспорядки.'`:
```
[['Президент Филиппин заявил,', 'что поедет на дачу, если будут беспорядки.', 'attribution', 'SN'], 
 ['что поедет на дачу,', 'если будут беспорядки.', 'condition', 'NS']]
```  

# Cite 

https://link.springer.com/chapter/10.1007/978-3-030-72610-2_8  

* Gost:
Chistova E., Shelmanov A., Pisarevskaya D., Kobozeva M. and Isakov V., Panchenko A., Toldova S. and Smirnov I. RST Discourse Parser for Russian: An Experimental Study of Deep Learning Models // Proceedings of Analysis of Images, Social Networks and Texts (AIST). — 2020. — P. 105-119.

* BibTeX:
```
@inproceedings{chistova2020rst,
  title={{RST} Discourse Parser for {R}ussian: An Experimental Study of Deep Learning Models},
  author={Chistova, Elena and Shelmanov, Artem and Pisarevskaya, Dina and Kobozeva, Maria and Isakov, Vadim  and Panchenko, Alexander  and Toldova, Svetlana  and Smirnov, Ivan },
  booktitle={In Proceedings of Analysis of Images, Social Networks and Texts (AIST)},
  pages={105--119},
  year={2020}
}
```


* Springer:
Chistova E. et al. (2021) RST Discourse Parser for Russian: An Experimental Study of Deep Learning Models. In: van der Aalst W.M.P. et al. (eds) Analysis of Images, Social Networks and Texts. AIST 2020. Lecture Notes in Computer Science, vol 12602. Springer, Cham. https://doi.org/10.1007/978-3-030-72610-2_8  
