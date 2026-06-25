import { Navigate, Route, Routes } from 'react-router-dom'
import Login from '@pages/Login'
import Dashboard from '@pages/Dashboard'
import Settings from '@pages/Settings'
import Customers from '@pages/Customers/Index'
import PromotionsIndex from '@pages/Promotions/Index'
import PromotionNew from '@pages/Promotions/New'
import PromotionDetail from '@pages/Promotions/Detail'
import PromotionSimulator from '@pages/Promotions/Simulator'
import Appointments from '@pages/Appointments/Index'
import NoShowBlocked from '@pages/NoShowBlocked/Index'
import Followups from '@pages/Followups/Index'
import Reports from '@pages/Reports/Index'
import Retention from '@pages/Retention/Index'
import Professionals from '@pages/Professionals/Index'
import StaffList from '@pages/Staff/Index'
import StaffNew from '@pages/Staff/New'
import StaffEdit from '@pages/Staff/Edit'
import ServicesPage from '@pages/Services/Index'
import TenantsIndex from '@pages/Tenants/Index'
import CronJobsPage from '@pages/Admin/CronJobs'
import TenantTrackerPage from '@pages/Admin/TenantTracker'
import CartsPage from '@pages/Store/Carts'
import OrdersPage from '@pages/Store/Orders'
import ProductsPage from '@pages/Store/Products'
import CategoriesPage from '@pages/Store/Categories'
import OffersPage from '@pages/Store/Offers'
import StoreCatalogPage from '@pages/Store/Catalog'
import Layout from '@components/Layout'
import RequireCapability from '@components/RequireCapability'
import { ProtectedRoute } from '@components/ProtectedRoute'
import WhatsAppMenusIndex from '@pages/WhatsApp/MenusIndex'
import WhatsAppMenuEditor from '@pages/WhatsApp/MenuEditor'
import WhatsAppConfigPage from '@pages/WhatsApp/Config'
import WhatsAppTriggersIndex from '@pages/WhatsApp/TriggersIndex'
import WhatsAppTriggerEdit from '@pages/WhatsApp/TriggerEdit'
import WhatsAppMenuWizard from '@pages/WhatsApp/MenuWizard'
import WhatsAppBotModule from '@pages/WhatsApp/BotModule'
import WhatsAppMessageTemplatesPage from '@pages/WhatsApp/MessageTemplates'
import WorkflowManager from '@pages/WhatsApp/WorkflowManager'
import PublicCatalog from '@pages/PublicCatalog'
import AIIndex from '@pages/AI/Index'
import AppointmentsAssist from '@pages/AI/AppointmentsAssist'
import AIConfig from '@pages/AI/Config'
import AIPredictions from '@pages/AI/Predictions'
import { AuthProvider } from '@contexts/AuthContext'

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/ss-business/:tenant/catalog" element={<PublicCatalog />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
        <Route index element={<RequireCapability cap="core.dashboard"><Dashboard /></RequireCapability>} />
        <Route path="settings" element={
          <RequireCapability cap="core.settings"><Settings /></RequireCapability>
        } />
        <Route path="customers" element={
          <RequireCapability cap="core.customers"><Customers /></RequireCapability>
        } />
        <Route path="promotions" element={
          <RequireCapability cap="core.promotions"><PromotionsIndex /></RequireCapability>
        } />
        <Route path="promotions/new" element={
          <RequireCapability cap="core.promotions"><PromotionNew /></RequireCapability>
        } />
        <Route path="promotions/:id" element={
          <RequireCapability cap="core.promotions"><PromotionDetail /></RequireCapability>
        } />
        <Route path="promotions/simulator" element={
          <RequireCapability cap="core.promotions"><PromotionSimulator /></RequireCapability>
        } />
        <Route path="appointments" element={
          <RequireCapability cap="salon.appointments"><Appointments /></RequireCapability>
        } />
        <Route path="no-show-blocked" element={
          <RequireCapability cap="salon.no_show_blocked"><NoShowBlocked /></RequireCapability>
        } />
        <Route path="followups" element={
          <RequireCapability cap="core.followups"><Followups /></RequireCapability>
        } />
        <Route path="reports" element={
          <RequireCapability cap="core.reports"><Reports /></RequireCapability>
        } />
        <Route path="retention" element={
          <RequireCapability cap="core.retention"><Retention /></RequireCapability>
        } />
        <Route path="professionals" element={
          <RequireCapability cap="salon.professionals"><Professionals /></RequireCapability>
        } />
        <Route path="services" element={
          <RequireCapability cap="salon.services"><ServicesPage /></RequireCapability>
        } />
        <Route path="staff" element={
          <RequireCapability cap="core.staff"><StaffList /></RequireCapability>
        } />
        <Route path="staff/new" element={
          <RequireCapability cap="core.staff"><StaffNew /></RequireCapability>
        } />
        <Route path="staff/:id" element={
          <RequireCapability cap="core.staff"><StaffEdit /></RequireCapability>
        } />
        <Route path="tenants" element={
          <RequireCapability cap="core.tenants"><TenantsIndex /></RequireCapability>
        } />
        <Route path="admin/tenant-tracker" element={<TenantTrackerPage />} />
        <Route path="admin/cron-jobs" element={
          <RequireCapability cap="core.tenants"><CronJobsPage /></RequireCapability>
        } />
        <Route path="tenants/new" element={<Navigate to="/tenants?new=1" replace />} />
        <Route path="store/carts" element={
          <RequireCapability cap="store.orders"><CartsPage /></RequireCapability>
        } />
        <Route path="store/orders" element={
          <RequireCapability cap="store.orders"><OrdersPage /></RequireCapability>
        } />
        <Route path="store/products" element={
          <RequireCapability cap="store.catalog"><ProductsPage /></RequireCapability>
        } />
        <Route path="store/categories" element={
          <RequireCapability cap="store.catalog"><CategoriesPage /></RequireCapability>
        } />
        <Route path="store/offers" element={
          <RequireCapability cap="store.catalog"><OffersPage /></RequireCapability>
        } />
        <Route path="store/catalog" element={
          <RequireCapability cap="store.catalog"><StoreCatalogPage /></RequireCapability>
        } />
        <Route path="whatsapp" element={
          <RequireCapability cap="core.whatsapp_menu"><WhatsAppMenusIndex /></RequireCapability>
        } />
        <Route path="whatsapp/wizard" element={
          <RequireCapability cap="core.whatsapp_menu"><WhatsAppMenuWizard /></RequireCapability>
        } />
        <Route path="whatsapp/triggers" element={
          <RequireCapability cap="core.whatsapp_menu"><WhatsAppTriggersIndex /></RequireCapability>
        } />
        <Route path="whatsapp/triggers/:id" element={
          <RequireCapability cap="core.whatsapp_menu"><WhatsAppTriggerEdit /></RequireCapability>
        } />
        <Route path="whatsapp/menus/:id" element={
          <RequireCapability cap="core.whatsapp_menu"><WhatsAppMenuEditor /></RequireCapability>
        } />
        <Route path="whatsapp/config" element={
          <RequireCapability cap="core.whatsapp_menu"><WhatsAppConfigPage /></RequireCapability>
        } />
        <Route path="whatsapp/messages" element={
          <RequireCapability cap="core.whatsapp_menu"><WhatsAppMessageTemplatesPage /></RequireCapability>
        } />
        <Route path="whatsapp/workflows" element={
          <RequireCapability cap="core.whatsapp_menu"><WorkflowManager /></RequireCapability>
        } />
        <Route path="whatsapp/bot" element={
          <RequireCapability cap="core.whatsapp_menu"><WhatsAppBotModule /></RequireCapability>
        } />
        {/** AI hub kept ungated; sub-pages gated by capabilities **/}
        <Route path="ai" element={<AIIndex />} />
        <Route path="ai/appointments" element={
          <RequireCapability cap="ai.appointment_recs"><AppointmentsAssist /></RequireCapability>
        } />
        <Route path="ai/config" element={
          <RequireCapability cap="core.settings"><AIConfig /></RequireCapability>
        } />
        <Route path="ai/predictions" element={
          <RequireCapability cap="ai.predictions"><AIPredictions /></RequireCapability>
        } />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}
