import pandas as pd
from isanlp.annotation_rst import DiscourseUnit

from symbol_map import SYMBOL_MAP


class RSTTreePredictor:
    """
    Contains classifiers and processors needed for tree building.
    """

    def __init__(self, features_processor, relation_predictor_sentence, relation_predictor_text, label_predictor,
                 nuclearity_predictor):
        self.features_processor = features_processor
        self.relation_predictor_sentence = relation_predictor_sentence
        self.relation_predictor_text = relation_predictor_text
        self.label_predictor = label_predictor

        self.nuclearity_predictor = nuclearity_predictor
        if self.nuclearity_predictor:
            self.nuclearities = self.nuclearity_predictor.classes_

        self.genre = None

        self.DEFAULT_RELATION = 'joint_NN'

        self._penalty_words = []

    def _find_penalty_words(self, span, _penalty=0.5):
        if len(span.split()) > 100:
            return _penalty

        for word in self._penalty_words:
            if word in span.lower():
                return _penalty

        for word in ['.', '?', '!']:
            return _penalty / 2.

        return 0


class GoldTreePredictor(RSTTreePredictor):
    """
    Contains classifiers and processors needed for gold tree building from corpus.
    """

    def __init__(self, corpus):
        """
        :param pandas.DataFrame corpus:
            columns=['snippet_x', 'snippet_y', 'category_id']
            rows=[all the relations pairs from corpus]
        """
        RSTTreePredictor.__init__(self, None, None, None, None, None)
        self.corpus = corpus
        self._symbol_map = SYMBOL_MAP

        for key, value in self._symbol_map.items():
            self.corpus.snippet_x = self.corpus.snippet_x.replace(key, value, regex=True)
            self.corpus.snippet_y = self.corpus.snippet_y.replace(key, value, regex=True)

    def extract_features(self, *args):
        features = pd.DataFrame({
            'snippet_x': [args[0].text, ],
            'snippet_y': [args[1].text, ]
        })

        for key, value in self._symbol_map.items():
            features.snippet_x = features.snippet_x.replace(key, value, regex=True)
            features.snippet_y = features.snippet_y.replace(key, value, regex=True)

        return features

    def initialize_features(self, *args):
        features = pd.DataFrame({
            'snippet_x': [args[0][i].text for i in range(len(args[0]) - 1)],
            'snippet_y': [args[0][i].text for i in range(1, len(args[0]))]
        })

        for key, value in self._symbol_map.items():
            features.snippet_x = features.snippet_x.replace(key, value, regex=True)
            features.snippet_y = features.snippet_y.replace(key, value, regex=True)

        return features

    def predict_pair_proba(self, features, _same_sentence_bonus=0.):
        def _check_snippet_pair_in_dataset(left_snippet, right_snippet):
            proba = float(((self.corpus.snippet_x == left_snippet) & (self.corpus.snippet_y == right_snippet)).sum(
                axis=0) != 0)

            return min(1., proba)

        result = features.apply(lambda row: _check_snippet_pair_in_dataset(row.snippet_x, row.snippet_y), axis=1)
        return result.values.tolist()

    def predict_label(self, features):
        def _get_label(left_snippet, right_snippet):
            joint = self.corpus[
                ((self.corpus.snippet_x == left_snippet) & (self.corpus.snippet_y == right_snippet))]
            label = joint.category_id.map(lambda row: row.split('_')[0]) + '_' + joint.order
            label = label.values

            if label.size == 0:
                return self.DEFAULT_RELATION

            return label[0]

        if type(features) == pd.Series:
            result = _get_label(features.loc['snippet_x'], features.loc['snippet_y'])
            return result
        else:
            result = features.apply(lambda row: _get_label(row.snippet_x, row.snippet_y), axis=1)
            return result.values.tolist()

    def predict_nuclearity(self, features):
        def _get_nuclearity(left_snippet, right_snippet):
            nuclearity = self.corpus[
                ((self.corpus.snippet_x == left_snippet) & (self.corpus.snippet_y == right_snippet))].order.values
            if nuclearity.size == 0:
                return '_'

        if type(features) == pd.Series:
            result = _get_nuclearity(features.loc['snippet_x'], features.loc['snippet_y'])
            return result
        else:
            result = features.apply(lambda row: _get_nuclearity(row.snippet_x, row.snippet_y), axis=1)
            return result.values.tolist()


class CustomTreePredictor(RSTTreePredictor):
    """
    Contains trained classifiers and feature processors needed for tree prediction.
    """

    def __init__(self, features_processor, relation_predictor_sentence, relation_predictor_text, label_predictor=None,
                 nuclearity_predictor=None):
        RSTTreePredictor.__init__(self, features_processor, relation_predictor_sentence, relation_predictor_text,
                                  label_predictor, nuclearity_predictor)

    def extract_features(self, left_node: DiscourseUnit, right_node: DiscourseUnit,
                         annot_text, annot_tokens, annot_sentences, annot_lemma, annot_morph, annot_postag,
                         annot_syntax_dep_tree):
        pair = pd.DataFrame({
            'snippet_x': [left_node.text.strip()],
            'snippet_y': [right_node.text.strip()],
            'loc_x': [left_node.start],
            'loc_y': [right_node.start]
        })

        try:
            features = self.features_processor(pair, annot_text=annot_text,
                                               annot_tokens=annot_tokens, annot_sentences=annot_sentences,
                                               annot_postag=annot_postag, annot_morph=annot_morph,
                                               annot_lemma=annot_lemma, annot_syntax_dep_tree=annot_syntax_dep_tree)
            if 'index' in features.keys():
                del features['index']

            return features

        except:
            with open('errors.log', 'w+') as f:
                f.write(str(pair.values))
                f.write(annot_text)
            return -1

    def initialize_features(self, nodes,
                            annot_text, annot_tokens, annot_sentences, annot_lemma, annot_morph, annot_postag,
                            annot_syntax_dep_tree):
        pairs = pd.DataFrame({
            'snippet_x': [node.text.strip() for node in nodes[:-1]],
            'snippet_y': [node.text.strip() for node in nodes[1:]],
            'loc_x': [node.start for node in nodes[:-1]],
            'loc_y': [node.start for node in nodes[1:]]
        })

        try:
            features = self.features_processor(pairs, annot_text=annot_text,
                                               annot_tokens=annot_tokens, annot_sentences=annot_sentences,
                                               annot_postag=annot_postag, annot_morph=annot_morph,
                                               annot_lemma=annot_lemma, annot_syntax_dep_tree=annot_syntax_dep_tree)
            if 'index' in features.keys():
                del features['index']

            return features

        except IndexError:
            with open('feature_extractor_errors.log', 'w+') as f:
                f.write(str(pairs.values))
                f.write(annot_text)
            return -1

    def predict_pair_proba(self, features, _same_sentence_bonus=0.5):

        if type(features) == pd.DataFrame:
            feat_same_sent = features[:]
            feat_same_sent.snippet_x = feat_same_sent.apply(lambda row: (row.same_sentence == 1) * row.snippet_x + '',
                                                            axis=1)
            feat_same_sent.snippet_y = feat_same_sent.apply(lambda row: (row.same_sentence == 1) * row.snippet_y + '',
                                                            axis=1)
            probas_sentence_level = self.relation_predictor_sentence.predict_proba(feat_same_sent)

            feat_not_same_sent = features[:]
            feat_not_same_sent.snippet_x = feat_not_same_sent.apply(
                lambda row: (row.same_sentence == 0) * row.snippet_x + '', axis=1)
            feat_not_same_sent.snippet_y = feat_not_same_sent.apply(
                lambda row: (row.same_sentence == 0) * row.snippet_y + '', axis=1)
            probas_text_level = self.relation_predictor_text.predict_proba(feat_not_same_sent)

            same_sentence_bonus = list(map(lambda value: float(value) * _same_sentence_bonus,
                                           list(features['same_sentence'] == 1)))
            return [probas_sentence_level[i][1] + same_sentence_bonus[i] + probas_text_level[i][1] for i in
                    range(len(probas_sentence_level))]

        if type(features) == pd.Series:
            if features.loc['same_sentence'] == 1:
                return self.relation_predictor_sentence.predict_proba(features)[0][1] + _same_sentence_bonus

            return self.relation_predictor_text.predict_proba(features)[0][1]

        if type(features) == list:
            return self.relation_predictor_text.predict_proba([features])[0][1]

    def predict_label(self, features):
        if not self.label_predictor:
            return 'relation'

        if type(features) == pd.DataFrame:
            return self.label_predictor.predict(features)

        if type(features) == pd.Series:
            return self.label_predictor.predict(features.to_frame().T)[0]

    def predict_nuclearity(self, features):
        if not self.nuclearity_predictor:
            return 'unavail'

        if type(features) == pd.DataFrame:
            return self.nuclearity_predictor.predict(features)

        if type(features) == pd.Series:
            return self.nuclearity_predictor.predict(features.to_frame().T)[0]


class NNTreePredictor(CustomTreePredictor):
    """
    Contains trained classifiers and feature processors needed for tree prediction.
    """

    def extract_features(self, left_node: DiscourseUnit, right_node: DiscourseUnit,
                         annot_text, annot_tokens, annot_sentences, annot_lemma, annot_morph, annot_postag,
                         annot_syntax_dep_tree):
        pair = pd.DataFrame({
            'snippet_x': [left_node.text.strip()],
            'snippet_y': [right_node.text.strip()],
            'loc_x': [left_node.start],
            'loc_y': [right_node.start]
        })

        features = self.features_processor(pair, annot_text=annot_text,
                                           annot_tokens=annot_tokens, annot_sentences=annot_sentences,
                                           annot_postag=annot_postag, annot_morph=annot_morph,
                                           annot_lemma=annot_lemma, annot_syntax_dep_tree=annot_syntax_dep_tree)

        if 'index' in features.keys():
            del features['index']

        features['snippet_x'] = features['snippet_x_tokens'].map(
            lambda row: ' '.join([token.text for token in row])).values
        features['snippet_y'] = features['snippet_y_tokens'].map(
            lambda row: ' '.join([token.text for token in row])).values

        return features

    def initialize_features(self, nodes,
                            annot_text, annot_tokens, annot_sentences, annot_lemma, annot_morph, annot_postag,
                            annot_syntax_dep_tree):
        features = super().initialize_features(nodes,
                                               annot_text=annot_text,
                                               annot_tokens=annot_tokens, annot_sentences=annot_sentences,
                                               annot_postag=annot_postag, annot_morph=annot_morph,
                                               annot_lemma=annot_lemma, annot_syntax_dep_tree=annot_syntax_dep_tree)

        features['snippet_x'] = features['snippet_x_tokens'].map(
            lambda row: ' '.join([token.text for token in row])).values
        features['snippet_y'] = features['snippet_y_tokens'].map(
            lambda row: ' '.join([token.text for token in row])).values

        return features

    def predict_pair_proba(self, features, _same_sentence_bonus=0.1):

        if type(features) == pd.DataFrame:
            probas_text_level = self.relation_predictor_text.predict_proba_batch(
                features['snippet_x'].values.tolist(),
                features['snippet_y'].values.tolist())

            sentence_level_map = list(map(float, list(features['same_sentence'] == 1)))

            return [probas_text_level[i][1] + _same_sentence_bonus * sentence_level_map[i] for i in
                    range(len(probas_text_level))]

        if type(features) == pd.Series:
            return self.relation_predictor_text.predict_proba(features.loc['snippet_x'],
                                                              features.loc['snippet_y'])[0][1] + (
                           features.loc['same_sentence'] == 1) * _same_sentence_bonus

        if type(features) == list:
            snippet_x = [feature['snippet_x'] for feature in features]
            snippet_y = [feature['snippet_y'] for feature in features]

            probas = self.relation_predictor_text.predict_proba_batch(snippet_x, snippet_y)

            return [proba[1] for proba in probas]

    def predict_label(self, features):

        result = self.DEFAULT_RELATION

        if not self.label_predictor:
            return result

        if type(features) == pd.DataFrame:
            result = self.label_predictor.predict_batch(features['snippet_x'].values.tolist(),
                                                        features['snippet_y'].values.tolist())

        if type(features) == pd.Series:
            result = self.label_predictor.predict(features.loc['snippet_x'],
                                                  features.loc['snippet_y'])

        if type(result) == list:
            return [_class_mapper.get(value) if _class_mapper.get(value) else value for value in result]

        if _class_mapper.get(result):
            return _class_mapper.get(result)

        return result


class LargeNNTreePredictor(NNTreePredictor):
    """
    Contains trained classifiers and feature processors needed for tree prediction.
    """

    def predict_pair_proba(self, features, _same_sentence_bonus=1.):

        if type(features) == pd.DataFrame:
            probas_text_level = self.relation_predictor_text.predict_proba_batch(
                features['snippet_x'].values.tolist(),
                features['snippet_y'].values.tolist(),
                # features['same_sentence'].map(str).values.tolist(),
                # features['same_paragraph'].map(str).values.tolist())
                features['at_paragraph_start_x'].map(str).values.tolist(),
                features['at_paragraph_start_y'].map(str).values.tolist())

            sentence_level_map = list(map(float, list(features['same_sentence'] == 1)))

            return [probas_text_level[i][1] + _same_sentence_bonus * sentence_level_map[i] for i in
                    range(len(probas_text_level))]

        if type(features) == pd.Series:
            return self.relation_predictor_text.predict_proba(features.loc['snippet_x'],
                                                              features.loc['snippet_y'],
                                                              str(features.loc['at_paragraph_start_x']),
                                                              str(features.loc['at_paragraph_start_y']))[0][1] + (
                           features.loc['same_sentence'] == 1) * _same_sentence_bonus

        if type(features) == list:
            snippet_x = [feature['snippet_x'] for feature in features]
            snippet_y = [feature['snippet_y'] for feature in features]
            at_paragraph_start_x = [feature['at_paragraph_start_x'].map(str) for feature in features]
            at_paragraph_start_y = [feature['at_paragraph_start_y'].map(str) for feature in features]

            probas = self.relation_predictor_text.predict_proba_batch(snippet_x, snippet_y, at_paragraph_start_x,
                                                                      at_paragraph_start_y)
            sentence_level_map = list(map(float, [feature['same_sentence'] == 1 for feature in features]))

            return [probas[i][1] + sentence_level_map[i] for i in range(len(probas))]

    def predict_label(self, features):

        result = self.DEFAULT_RELATION

        if not self.label_predictor:
            return result

        if type(features) == pd.DataFrame:
            result = self.label_predictor.predict_batch(features['snippet_x'].values.tolist(),
                                                        features['snippet_y'].values.tolist())

        if type(features) == pd.Series:
            result = self.label_predictor.predict(features.loc['snippet_x'],
                                                  features.loc['snippet_y'])

        return result


class ContextualNNTreePredictor(NNTreePredictor):
    """
    Contains trained classifiers and feature processors needed for tree prediction.
    """

    def predict_pair_proba(self, features, _same_sentence_bonus=.5):

        if type(features) == pd.DataFrame:
            probas_text_level = self.relation_predictor_text.predict_proba_batch(
                features['snippet_x'].values.tolist(),
                features['snippet_y'].values.tolist(),
                features['same_sentence'].map(str).values.tolist(),
                features['left_context'].values.tolist(),
                features['right_context'].values.tolist())

            sentence_level_map = list(map(float, list(features['same_sentence'] == 1)))

            return [probas_text_level[i][1] + _same_sentence_bonus * sentence_level_map[i] for i in
                    range(len(probas_text_level))]

        if type(features) == pd.Series:
            return self.relation_predictor_text.predict_proba(features.loc['snippet_x'],
                                                              features.loc['snippet_y'],
                                                              str(features.loc['same_sentence'],
                                                                  features.loc['left_context'],
                                                                  features.loc['right_context']))[0][1] + (
                           features.loc['same_sentence'] == 1) * _same_sentence_bonus

        if type(features) == list:
            snippet_x = [feature['snippet_x'] for feature in features]
            snippet_y = [feature['snippet_y'] for feature in features]
            same_sentence = [feature['same_sentence'].map(str) for feature in features]

            probas = self.relation_predictor_text.predict_proba_batch(snippet_x, snippet_y, same_sentence,
                                                                      left_context, right_context)
            sentence_level_map = list(map(float, [feature['same_sentence'] == 1 for feature in features]))

            return [probas[i][1] + sentence_level_map[i] for i in range(len(probas))]

    def predict_label(self, features):

        result = self.DEFAULT_RELATION

        if not self.label_predictor:
            return result

        if type(features) == pd.DataFrame:
            result = self.label_predictor.predict_batch(features['snippet_x'].values.tolist(),
                                                        features['snippet_y'].values.tolist())

        if type(features) == pd.Series:
            result = self.label_predictor.predict(features.loc['snippet_x'],
                                                  features.loc['snippet_y'])

        return result


class EnsembleNNTreePredictor(LargeNNTreePredictor):
    """
    Contains trained classifiers and feature processors needed for tree prediction.
    Instead of pure allennlp classification model, as is in LargeNNTreePredictor,
      predicts labels from an ensemble of allennlp and sklearn models.
    """

    def predict_label(self, features):

        result = self.DEFAULT_RELATION

        if not self.label_predictor:
            return result

        if type(features) == pd.DataFrame:
            result = self.label_predictor.predict_batch(snippet_x=features['snippet_x'].values.tolist(),
                                                        snippet_y=features['snippet_y'].values.tolist(),
                                                        features=features)

        if type(features) == pd.Series:
            result = self.label_predictor.predict(snippet_x=features.loc['snippet_x'],
                                                  snippet_y=features.loc['snippet_y'],
                                                  features=features.to_frame().T)

        return result


class DoubleEnsembleNNTreePredictor(EnsembleNNTreePredictor):
    """
    Contains trained classifiers and feature processors needed for tree prediction.
    Instead of pure allennlp classification model, as is in LargeNNTreePredictor,
      predicts labels from an ensemble of allennlp and sklearn models.
    Instead of pure sklearn classification model, as is in LargeNNTreePredictor,
      predicts structure from an ensemble of allennlp and sklearn models.
    """

    def predict_pair_proba(self, features, _same_sentence_bonus=1.):

        if type(features) == pd.DataFrame:
            probas_text_level = self.relation_predictor_text.predict_proba_batch(
                snippet_x=features['snippet_x'].values.tolist(),
                snippet_y=features['snippet_y'].values.tolist(),
                same_sentence=features['at_paragraph_start_x'].map(str).values.tolist(),
                same_paragraph=features['at_paragraph_start_y'].map(str).values.tolist(),
                features=features)

            # plus bonus for the presense in the same sentence
            sentence_level_map = list(map(float, list(features['same_sentence'] == 1)))

            return [probas_text_level[i][1] + _same_sentence_bonus * sentence_level_map[i] for i in
                    range(len(probas_text_level))]

        if type(features) == pd.Series:
            return self.relation_predictor_text.predict_proba(
                snippet_x=features.loc['snippet_x'],
                snippet_y=features.loc['snippet_y'],
                same_sentence=str(features.loc['at_paragraph_start_x']),
                same_paragraph=str(features.loc['at_paragraph_start_y']),
                features=features)[0][1] + (features.loc['same_sentence'] == 1) * _same_sentence_bonus

        if type(features) == list:
            snippet_x = [feature['snippet_x'] for feature in features]
            snippet_y = [feature['snippet_y'] for feature in features]
            at_paragraph_start_x = [feature['at_paragraph_start_x'].map(str) for feature in features]
            at_paragraph_start_y = [feature['at_paragraph_start_y'].map(str) for feature in features]

            probas = self.relation_predictor_text.predict_proba_batch(
                snippet_x=snippet_x,
                snippet_y=snippet_y,
                same_sentence=at_paragraph_start_x,
                same_paragraph=at_paragraph_start_y,
                features=features)

            sentence_level_map = list(map(float, [feature['same_sentence'] == 1 for feature in features]))

            return [probas[i][1] + sentence_level_map[i] for i in range(len(probas))]


class TopDownRSTPredictor:
    def __init__(self, features_processor, label_predictor):
        self.features_processor = features_processor
        self.label_predictor = label_predictor
