from thelpviewer.converter.base import PositionedKeyword, TopicRecord
from thelpviewer.converter.readers.ng import _remove_unresolved_ng_links


def test_unresolved_internal_pointers_keep_visible_text_without_dead_links():
    topic = TopicRecord(
        context_id=1,
        raw_lines=[b"Valid Missing"],
        uhf_content=[
            "[link:topic=2]Valid[/link] [link:topic=99][b]Missing[/b][/link]"
        ],
        positional_keywords=[
            PositionedKeyword(target_context=2, line=1, first_column=1, last_column=5),
            PositionedKeyword(target_context=99, line=1, first_column=7, last_column=13),
        ],
        up_context=99,
        next_context=2,
    )

    _remove_unresolved_ng_links(topic, {1, 2})

    assert topic.uhf_content == ["[link:topic=2]Valid[/link] [b]Missing[/b]"]
    assert [keyword.target_context for keyword in topic.positional_keywords] == [2]
    assert topic.up_context is None
    assert topic.next_context == 2
