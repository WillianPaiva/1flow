CREATE TABLE "core_language" (
    "id" serial NOT NULL PRIMARY KEY,
    "name" varchar(128) NOT NULL,
    "dj_code" varchar(16) NOT NULL UNIQUE,
    "parent_id" integer REFERENCES "core_language" ("id") DEFERRABLE INITIALLY DEFERRED,
    "duplicate_of_id" integer REFERENCES "core_language" ("id") DEFERRABLE INITIALLY DEFERRED,
    "lft" integer CHECK ("lft" >= 0) NOT NULL,
    "rght" integer CHECK ("rght" >= 0) NOT NULL,
    "tree_id" integer CHECK ("tree_id" >= 0) NOT NULL,
    "level" integer CHECK ("level" >= 0) NOT NULL
)
;
ALTER TABLE core_language OWNER TO oneflow;

CREATE TABLE "core_simpletag" (
    "id" serial NOT NULL PRIMARY KEY,
    "duplicate_of_id" integer REFERENCES "core_simpletag" ("id") DEFERRABLE INITIALLY DEFERRED,
    "name" varchar(128) NOT NULL,
    "slug" varchar(128),
    "language_id" integer REFERENCES "core_language" ("id") DEFERRABLE INITIALLY DEFERRED,
    "parent_id" integer REFERENCES "core_simpletag" ("id") DEFERRABLE INITIALLY DEFERRED,
    "origin_type_id" integer REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED,
    "origin_id" integer CHECK ("origin_id" >= 0),
    "lft" integer CHECK ("lft" >= 0) NOT NULL,
    "rght" integer CHECK ("rght" >= 0) NOT NULL,
    "tree_id" integer CHECK ("tree_id" >= 0) NOT NULL,
    "level" integer CHECK ("level" >= 0) NOT NULL,
    UNIQUE ("name", "language_id")
)
;
ALTER TABLE core_simpletag OWNER TO oneflow;
