export type WatchlistItemRow = {
  id: string;
  user_id: string;
  symbol: string;
  exchange: string;
  created_at: string;
  updated_at: string;
};

export type Database = {
  public: {
    Tables: {
      watchlist_items: {
        Row: WatchlistItemRow;
        Insert: { id?: string; user_id: string; symbol: string; exchange?: string; created_at?: string; updated_at?: string };
        Update: { symbol?: string; exchange?: string; updated_at?: string };
        Relationships: [];
      };
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
    Enums: Record<string, never>;
    CompositeTypes: Record<string, never>;
  };
};
