import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { HomePage } from "./pages/HomePage";
import { VacancyDetailPage } from "./pages/VacancyDetailPage";
import { BeheerPage } from "./pages/BeheerPage";
import { MatchPage } from "./pages/MatchPage";
import { MatchUitlegPage } from "./pages/MatchUitlegPage";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/vacatures/:slug" element={<VacancyDetailPage />} />
          <Route path="/beheer" element={<BeheerPage />} />
          <Route path="/match" element={<MatchPage />} />
          <Route path="/match/uitleg" element={<MatchUitlegPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
