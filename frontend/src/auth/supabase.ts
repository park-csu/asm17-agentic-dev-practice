import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);

function createSupabaseClient() {
  if (!supabaseUrl || !supabaseAnonKey) {
    return null;
  }
  return createClient(supabaseUrl, supabaseAnonKey);
}

export const supabase = createSupabaseClient();

export async function signInWithGoogle() {
  if (!supabase) {
    throw new Error("Supabase 설정이 필요합니다.");
  }

  const { error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: window.location.origin,
    },
  });
  if (error) {
    throw error;
  }
}

export async function signOut() {
  if (!supabase) {
    return;
  }
  const { error } = await supabase.auth.signOut();
  if (error) {
    throw error;
  }
}
