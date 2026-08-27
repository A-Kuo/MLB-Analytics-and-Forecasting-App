import { redirect } from "next/navigation";

// Analytics and Forecasts is the default page today (app.py's
// st.Page(..., default=True)) -- mirrored here.
export default function RootPage() {
  redirect("/analytics");
}
