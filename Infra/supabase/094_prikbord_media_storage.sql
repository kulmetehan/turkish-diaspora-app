-- 094_prikbord_media_storage.sql
-- Create Supabase Storage bucket for Prikbord media uploads

-- Note: This migration assumes Supabase Storage is enabled
-- The bucket needs to be created manually in Supabase Dashboard or via API
-- This SQL file documents the required bucket configuration

-- Bucket name: prikbord-media
-- Public: true (for public access to media)
-- File size limit: 50MB
-- Allowed MIME types: image/*, video/*

-- Storage policies (RLS policies for Supabase Storage)
-- These should be created via Supabase Dashboard or API

-- Policy: Allow authenticated users to upload
-- CREATE POLICY "Allow authenticated users to upload media"
-- ON storage.objects FOR INSERT
-- TO authenticated
-- WITH CHECK (bucket_id = 'prikbord-media');

-- Policy: Allow public read access
-- CREATE POLICY "Allow public read access to media"
-- ON storage.objects FOR SELECT
-- TO public
-- USING (bucket_id = 'prikbord-media');

-- Policy: Allow users to delete their own uploads
-- CREATE POLICY "Allow users to delete their own uploads"
-- ON storage.objects FOR DELETE
-- TO authenticated
-- USING (
--   bucket_id = 'prikbord-media' AND
--   (storage.foldername(name))[1] = auth.uid()::text
-- );

COMMENT ON SCHEMA storage IS 'Supabase Storage schema for file uploads';
COMMENT ON TABLE storage.objects IS 'Storage objects table managed by Supabase';





