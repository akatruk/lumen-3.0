# Multilingual media coverage

One library. Queries in English, Russian, and Chinese. Run against `media/library/search.py` after the phrase table in `media/library/concepts.py`.

20 concepts × 3 locales = 60 queries. All 60 returned a hit. None of the top hits were a decorative arrow. The top id matched across the three languages for 19 of the 20 concepts. Couple relocation differs by one relevant still (`people_property_001` in English, `people_couple_001` in Russian and Chinese).

| Concept | Top hit |
| --- | --- |
| immigration.second_passport | `doc_book_001` |
| relocation.family_planning | `people_door_001` |
| real_estate.property_investment | `re_inv_laptop` |
| immigration.document_consultation | `re_agent_docs` |
| travel.international_arrival | `people_door_001` |
| relocation.business | `imm_icon_business-move` |
| immigration.residency_application | `i2v_review_001` |
| real_estate.new_apartment | `people_property_001` |
| immigration.global_mobility | `global_route_001` |
| immigration.country_comparison | `imm_icon_country-comparison` |
| relocation.packing | `people_packing_001` |
| real_estate.property_viewing | `people_property_001` |
| real_estate.key_handover | `re_agent_keys` |
| immigration.citizenship_planning | `re_buyer_plan` |
| relocation.couple | `people_property_001` / `people_couple_001` |
| travel.city_arrival | `still_city_001` |
| real_estate.investor_meeting | `re_inv_meeting` |
| immigration.approval | `document_approval_001` |
| relocation.remote_work | `global_route_001` |
| relocation.family_home | `people_door_001` |

## Weak hits

These are relevant only in a loose sense. They are called out so they are not treated as solved:

- Citizenship planning opens the buyer-planning still, not a citizenship object. The line icon exists and ranks lower than the photograph.
- Business relocation opens a line icon. There is no photograph of a company move.
- Remote work abroad opens the route animation. `re_int_office` exists and is not winning this query.
- Second passport opens a blank booklet drawing. There is no second photograph of a generic booklet.

An unrecognized Chinese string with no alias now returns nothing, instead of the arrow set.

Assets stay language-neutral. Localized sentences are not baked into files. `conceptId` is not yet written onto each manifest row; the ids live in `concepts.py` so existing manifest readers keep working.
