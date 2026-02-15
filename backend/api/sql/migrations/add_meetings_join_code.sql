ALTER TABLE meetings
ADD COLUMN IF NOT EXISTS join_code VARCHAR(12) NULL;

DO $$
DECLARE
    rec RECORD;
    new_code VARCHAR(12);
    code_exists BOOLEAN;
BEGIN
    FOR rec IN SELECT id FROM meetings WHERE join_code IS NULL LOOP
        LOOP
            new_code := LPAD(FLOOR(RANDOM() * 1000000000000)::TEXT, 12, '0');
            SELECT EXISTS(SELECT 1 FROM meetings WHERE join_code = new_code) INTO code_exists;
            EXIT WHEN NOT code_exists;
        END LOOP;
        UPDATE meetings SET join_code = new_code WHERE id = rec.id;
    END LOOP;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_meetings_join_code ON meetings (join_code);

ALTER TABLE meetings
ALTER COLUMN join_code SET NOT NULL;

ALTER TABLE meetings
ALTER COLUMN passcode TYPE VARCHAR(6);

