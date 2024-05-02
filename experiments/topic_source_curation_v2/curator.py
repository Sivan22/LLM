"""
Main
"""
from experiments.topic_source_curation_v2.gather.source_gatherer import gather_sources_about_topic
from experiments.topic_source_curation_v2.cluster import get_clustered_sources
from sefaria.helper.llm.topic_prompt import _make_llm_topic
from sefaria_llm_interface.common.topic import Topic
from sefaria_llm_interface.topic_prompt import TopicPromptSource
from util.pipeline import Artifact

def curate_topic(topic: Topic) -> list[TopicPromptSource]:
    return (Artifact(topic)
            .pipe(gather_sources_about_topic)
            .pipe(get_clustered_sources, topic)
            .pipe().data)

if __name__ == '__main__':
    slug = "stars"
    topic = _make_llm_topic(slug)
    curate_topic(topic)

