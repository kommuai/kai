import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import AuthPage from "./pages/AuthPage";
import OAuthCallback from "./pages/OAuthCallback";
import DashboardPage from "./pages/DashboardPage";
import NewTenantPage from "./pages/NewTenantPage";
import TenantEditorPage from "./pages/TenantEditorPage";
import InboxPage from "./pages/InboxPage";
import ConversationPage from "./pages/ConversationPage";
import ContactsPage from "./pages/ContactsPage";
import AppShell from "./components/AppShell";
import TenantShell from "./components/TenantShell";
import ProtectedRoute from "./components/ProtectedRoute";

const qc = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          {/* Public */}
          <Route path="/login" element={<AuthPage />} />
          <Route path="/auth/callback" element={<OAuthCallback />} />

          {/* Protected */}
          <Route element={<ProtectedRoute />}>
            <Route element={<AppShell />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/tenants/new" element={<NewTenantPage />} />
              <Route path="/t/:slug" element={<TenantShell />}>
                <Route index element={<TenantEditorPage />} />
                <Route path="inbox" element={<InboxPage />}>
                  <Route path=":userId" element={<ConversationPage />} />
                </Route>
                <Route path="contacts" element={<ContactsPage />} />
              </Route>
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>

      <Toaster
        position="top-right"
        toastOptions={{
          duration: 3500,
          style: {
            borderRadius: "12px",
            boxShadow: "0 4px 12px rgb(0 0 0 / 0.1)",
            fontSize: "14px",
            fontFamily: "Inter, sans-serif",
          },
        }}
      />
    </QueryClientProvider>
  );
}
