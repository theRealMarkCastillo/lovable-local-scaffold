-- Sample application schema. Preserve imported app migrations/RLS when migrating.
CREATE TABLE public.notes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id uuid NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
  title text NOT NULL CHECK (length(title) BETWEEN 1 AND 120),
  body text NOT NULL DEFAULT '' CHECK (length(body) <= 4000),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX notes_owner_created ON public.notes(owner_id, created_at DESC);
ALTER TABLE public.notes ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.notes FROM anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.notes TO authenticated;
CREATE POLICY notes_select ON public.notes FOR SELECT TO authenticated USING ((SELECT auth.uid()) = owner_id);
CREATE POLICY notes_insert ON public.notes FOR INSERT TO authenticated WITH CHECK ((SELECT auth.uid()) = owner_id);
CREATE POLICY notes_update ON public.notes FOR UPDATE TO authenticated USING ((SELECT auth.uid()) = owner_id) WITH CHECK ((SELECT auth.uid()) = owner_id);
CREATE POLICY notes_delete ON public.notes FOR DELETE TO authenticated USING ((SELECT auth.uid()) = owner_id);
INSERT INTO storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
VALUES ('uploads','uploads',false,2097152,ARRAY['text/plain','application/json','image/png','image/jpeg']);
CREATE POLICY uploads_select ON storage.objects FOR SELECT TO authenticated USING (bucket_id='uploads' AND (storage.foldername(name))[1]=(SELECT auth.uid())::text);
CREATE POLICY uploads_insert ON storage.objects FOR INSERT TO authenticated WITH CHECK (bucket_id='uploads' AND (storage.foldername(name))[1]=(SELECT auth.uid())::text);
CREATE POLICY uploads_update ON storage.objects FOR UPDATE TO authenticated USING (bucket_id='uploads' AND (storage.foldername(name))[1]=(SELECT auth.uid())::text) WITH CHECK (bucket_id='uploads' AND (storage.foldername(name))[1]=(SELECT auth.uid())::text);
CREATE POLICY uploads_delete ON storage.objects FOR DELETE TO authenticated USING (bucket_id='uploads' AND (storage.foldername(name))[1]=(SELECT auth.uid())::text);
ALTER PUBLICATION supabase_realtime ADD TABLE public.notes;
NOTIFY pgrst, 'reload schema';
