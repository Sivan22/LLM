from experiments.topic_source_curation_v2.cache import load_sources, load_clusters
from sefaria_llm_interface.topic_prompt import TopicPromptSource
from sefaria_llm_interface.common.topic import Topic
import django
django.setup()
from sefaria.model.topic import Topic as SefariaTopic
from sefaria.helper.llm.topic_prompt import _make_llm_topic
from collections import defaultdict


def count_cats():
    sources = load_sources(_make_llm_topic(SefariaTopic.init('cyrus')))
    cat_counts = defaultdict(list)
    for source in sources:
        assert isinstance(source, TopicPromptSource)
        cat_counts[source.categories[0]] += [source.ref]
    for cat, trefs in cat_counts.items():
        print(f'{cat}: {len(trefs)}')
        for ref in trefs:
            print('\t', ref)


def print_clusters():
    clusters = load_clusters(_make_llm_topic(SefariaTopic.init('ants')))
    for cluster in clusters:
        print(f'{cluster.summary}: {len(cluster)}')
        for item in cluster.items:
            print('\t', item.source.ref)
            print('\t\t', item.summary)


if __name__ == '__main__':
    # count_cats()
    print_clusters()
