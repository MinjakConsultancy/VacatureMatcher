-- Scrape-bronnen als filter_sets (ikwerk / wbo); legacy breed/ict/all blijven bestaan

INSERT INTO filter_sets (id, label, query_params) VALUES
    ('ikwerk', 'IkWerk (ingelogd)', 'publishedSince'),
    ('wbo', 'Werkenbijdeoverheid (sitemap)', 'lastmod')
ON CONFLICT (id) DO NOTHING;
