import { redirect } from "next/navigation";

// Insights is the default page today (app.py's st.Page(..., default=True)
// on pages/insights.py) -- mirrored here.
export default function RootPage() {
  redirect("/insights");
}
