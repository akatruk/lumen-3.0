# Scene-context stock placement

External B-roll search now displays the selected Director Timeline scene's source range, title and overlapping transcript. Search remains user-entered; this is not a new semantic search provider or automatic AI query generator.

Completed imports have an inline private media preview and a placement action for the currently selected scene. Placement uses at most four seconds bounded by scene and asset duration, clears conflicting source cutaways, resets approval, and changes only the local draft. Save and approve are still required. Locked scenes and busy editors cannot receive placements. Existing controls allow adjusting source offset and insert range afterward. Source speech is preserved.

Validation: TypeScript/Vite production build passed. Headless Chrome component fixture checks search → imported result → selected-scene callback, then verifies the placement button disables for a locked/blocked scene. Backend/import/render paths are unchanged.
