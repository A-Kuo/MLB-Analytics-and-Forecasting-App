"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type NewsDrawerProps = {
  selectedTeamIds: number[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

type NewsItem = {
  id: string;
  headline: string;
  source: string;
  url: string;
  thumbnail_url?: string;
  published_at: string;
};

export function NewsDrawer({ selectedTeamIds, open, onOpenChange }: NewsDrawerProps) {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasFetched, setHasFetched] = useState(false);
  const [prevTeamIds, setPrevTeamIds] = useState<string>("");

  useEffect(() => {
    if (!open) return;

    const teamIdsStr = selectedTeamIds.join(",");
    
    // Only fetch if it's the first time opening, or if teamIds changed
    if (!hasFetched || prevTeamIds !== teamIdsStr) {
      const fetchNews = async () => {
        setLoading(true);
        setError(null);
        try {
          const url = teamIdsStr 
            ? `/api/news?teamIds=${teamIdsStr}`
            : `/api/news`;
          
          const res = await fetch(url);
          if (!res.ok) throw new Error("Failed to fetch news");
          
          const data = await res.json();
          setNews(data.data || []);
          setHasFetched(true);
          setPrevTeamIds(teamIdsStr);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Error fetching news");
        } finally {
          setLoading(false);
        }
      };

      fetchNews();
    }
  }, [open, selectedTeamIds, hasFetched, prevTeamIds]);

  return (
    <>
      {/* Backdrop */}
      {open && (
        <div 
          className="fixed inset-0 z-40 bg-black/50 transition-opacity md:hidden"
          onClick={() => onOpenChange(false)}
        />
      )}
      
      {/* Drawer */}
      <div 
        className={`fixed inset-y-0 right-0 z-50 w-full max-w-sm transform bg-[#1e1e1e] shadow-xl transition-transform duration-300 ease-in-out ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between border-b border-gray-800 p-4">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <span className="text-[#e31837]">MLB</span> News Feed
            </h2>
            <button 
              onClick={() => onOpenChange(false)}
              className="text-gray-400 hover:text-white"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            <h3 className="mb-4 text-sm font-semibold text-gray-400 uppercase tracking-wider">
              Headlines from the last 7 days
            </h3>
            
            {loading ? (
              <div aria-live="polite" className="space-y-4">
                {[1, 2, 3].map(i => (
                  <div key={i} className="animate-pulse flex gap-3">
                    <div className="w-16 h-16 bg-gray-800 rounded"></div>
                    <div className="flex-1 space-y-2">
                      <div className="h-4 bg-gray-800 rounded w-3/4"></div>
                      <div className="h-3 bg-gray-800 rounded w-1/2"></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : selectedTeamIds.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <p>Select a team to see its news.</p>
              </div>
            ) : error ? (
              <div className="text-center text-red-400 py-8">
                <p>{error}</p>
              </div>
            ) : news.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <p>No cached news is available yet. Run the ingestion workflow or wait for the next scheduled refresh.</p>
              </div>
            ) : (
              <div className="space-y-6">
                {news.map((item) => (
                  <article key={item.id} className="flex gap-3 group">
                    {item.thumbnail_url && (
                      <div className="flex-shrink-0">
                        <img 
                          src={item.thumbnail_url} 
                          alt="" 
                          className="w-16 h-16 object-cover rounded bg-gray-800"
                          loading="lazy"
                        />
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <Link 
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer" 
                        className="text-gray-200 font-medium group-hover:text-[#4b92db] line-clamp-2 transition-colors"
                      >
                        {item.headline}
                      </Link>
                      <div className="mt-1 flex items-center text-xs text-gray-500 gap-2">
                        <span className="truncate">{item.source}</span>
                        <span>•</span>
                        <span>{new Date(item.published_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
