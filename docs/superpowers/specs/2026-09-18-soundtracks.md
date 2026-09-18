# Reusable background music

User confirmed a curated background-music collection, rather than trending commercial songs. Provide a reusable, authenticated catalogue with preview, mood filter, favourites and the user's previously uploaded music. One click adds an immutable copy to an owned project; existing music selection, AI soundtrack proposals and renderer consume the normal project asset. Import never changes the saved edit or triggers a paid operation.

Seed six real Kevin MacLeod tracks from the official catalogue with source URL, CC BY 4.0 attribution and verified audio metadata. Keep files on the deployment host; catalogue metadata is versioned. Do not label the list a popularity ranking. Preserve author credits when reusing music. Users cannot access other users' private tracks or favourites. Import is idempotent per target project and source, respects the 20-asset ceiling, and stores files independently of the source project.

UI supports Russian, English and Chinese. Previews load only when played and pause one another. Disabled imports explain the full-library state. Empty favourites and uploaded-music tabs explain what to do. Render behavior is unchanged.
