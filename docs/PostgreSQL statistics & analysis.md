
# PostgreSQL indexes


## Most complete

http://stackoverflow.com/a/25596855/654755

    SELECT  
        c.relname AS table,
        f.attname AS column,  
        pg_catalog.format_type(f.atttypid,f.atttypmod) AS type,
        f.attnotnull AS notnull,  
        i.relname as index_name,
    CASE  
        WHEN i.oid<>0 THEN 'Y'  
        ELSE ''  
    END AS is_index,  
    CASE  
        WHEN p.contype = 'p' THEN 'Y'  
        ELSE ''  
    END AS primarykey,  
    CASE  
        WHEN p.contype = 'u' THEN 'Y' 
        WHEN p.contype = 'p' THEN 'Y' 
        ELSE ''
    END AS uniquekey,
    CASE
        WHEN f.atthasdef = 'Y' THEN d.adsrc
    END AS default  FROM pg_attribute f  
    JOIN pg_class c ON c.oid = f.attrelid  
    JOIN pg_type t ON t.oid = f.atttypid  
    LEFT JOIN pg_attrdef d ON d.adrelid = c.oid AND d.adnum = f.attnum  
    LEFT JOIN pg_namespace n ON n.oid = c.relnamespace  
    LEFT JOIN pg_constraint p ON p.conrelid = c.oid AND f.attnum = ANY (p.conkey)  
    LEFT JOIN pg_class AS g ON p.confrelid = g.oid
    LEFT JOIN pg_index AS ix ON f.attnum = ANY(ix.indkey) and c.oid = f.attrelid and c.oid = ix.indrelid 
    LEFT JOIN pg_class AS i ON ix.indexrelid = i.oid 

    WHERE c.relkind = 'r'::char  
    AND n.nspname = 'public'  -- Replace with Schema name 
    --AND c.relname = 'nodes'  -- Replace with table name, or Comment this for get all tables
    AND f.attnum > 0
    ORDER BY c.relname,f.attname;



## Simpler but very nice

http://stackoverflow.com/a/2213199/654755

    select                         
        t.relname as table_name,
        i.relname as index_name,
        a.attname as column_name
    from
        pg_class t,
        pg_class i,
        pg_index ix,
        pg_attribute a
    where
        t.oid = ix.indrelid
        and i.oid = ix.indexrelid
        and a.attrelid = t.oid
        and a.attnum = ANY(ix.indkey)
        and t.relkind = 'r'
    order by                      
        t.relname,
        i.relname;


    select
        t.relname as table_name,
        i.relname as index_name,
        array_to_string(array_agg(a.attname), ', ') as column_names
    from
        pg_class t,
        pg_class i,
        pg_index ix,
        pg_attribute a
    where
        t.oid = ix.indrelid
        and i.oid = ix.indexrelid
        and a.attrelid = t.oid
        and a.attnum = ANY(ix.indkey)
        and t.relkind = 'r'
    group by
        t.relname,
        i.relname
    order by
        t.relname,
        i.relname;



## As a view

    CREATE OR REPLACE VIEW view_index AS 
    SELECT
         n.nspname  as "schema"
        ,t.relname  as "table"
        ,c.relname  as "index"
        ,pg_get_indexdef(indexrelid) as "def"
    FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid    = c.relnamespace
        JOIN pg_catalog.pg_index i ON i.indexrelid = c.oid
        JOIN pg_catalog.pg_class t ON i.indrelid   = t.oid
    WHERE c.relkind = 'i'
        and n.nspname not in ('pg_catalog', 'pg_toast')
        and pg_catalog.pg_table_is_visible(c.oid)
    ORDER BY
         n.nspname
        ,t.relname
        ,c.relname;
