import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { dashboardAPI } from '../lib/api';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { FolderKanban, FileCode, Globe, Activity, Plus, ArrowRight } from 'lucide-react';

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [recentProjects, setRecentProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const res = await dashboardAPI.stats();
      setStats(res.data.stats);
      setRecentProjects(res.data.recent_projects);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  const statCards = stats ? [
    { label: 'PROJECTS', value: stats.total_projects, icon: FolderKanban, color: '#2563EB' },
    { label: 'SCRIPTS', value: stats.total_scripts, icon: FileCode, color: '#16A34A' },
    { label: 'DOMAINS', value: stats.total_whitelists, icon: Globe, color: '#F59E0B' },
    { label: 'REQUESTS', value: stats.total_requests, icon: Activity, color: '#8B5CF6' },
  ] : [];

  if (loading) {
    return (
      <Layout>
        <div className="animate-pulse space-y-6" data-testid="dashboard-loading">
          <div className="h-8 bg-slate-100 rounded w-48" />
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[1,2,3,4].map(i => <div key={i} className="h-28 bg-slate-100 rounded-lg" />)}
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-8" data-testid="dashboard-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
              Dashboard
            </h1>
            <p className="text-muted-foreground mt-1">Overview of your JavaScript hosting platform</p>
          </div>
          <Button
            onClick={() => navigate('/projects')}
            className="bg-[#0F172A] hover:bg-[#1E293B] text-white active:scale-95 transition-transform"
            data-testid="new-project-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Project
          </Button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6" data-testid="stats-grid">
          {statCards.map((stat) => (
            <Card key={stat.label} className="border border-border bg-white shadow-sm hover:shadow-md transition-shadow duration-200">
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <span className="label-caps">{stat.label}</span>
                  <div className="w-9 h-9 rounded-md flex items-center justify-center" style={{ backgroundColor: stat.color + '12' }}>
                    <stat.icon className="w-4 h-4" style={{ color: stat.color }} strokeWidth={1.5} />
                  </div>
                </div>
                <p className="text-3xl font-semibold tracking-tight font-mono" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                  {stat.value.toLocaleString()}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Request Stats */}
        {stats && stats.total_requests > 0 && (
          <Card className="border border-border bg-white shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg font-medium" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
                Request Distribution
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-8">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-green-500" />
                  <span className="text-sm text-muted-foreground">Allowed:</span>
                  <span className="text-sm font-semibold font-mono">{stats.total_allowed}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500" />
                  <span className="text-sm text-muted-foreground">Denied:</span>
                  <span className="text-sm font-semibold font-mono">{stats.total_denied}</span>
                </div>
              </div>
              <div className="mt-4 h-3 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full bg-green-500 rounded-full transition-all duration-500"
                  style={{ width: `${stats.total_requests > 0 ? (stats.total_allowed / stats.total_requests) * 100 : 0}%` }}
                />
              </div>
            </CardContent>
          </Card>
        )}

        {/* Recent Projects */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-medium tracking-tight" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
              Recent Projects
            </h2>
            <Button variant="ghost" size="sm" onClick={() => navigate('/projects')} data-testid="view-all-projects-btn">
              View all <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
          {recentProjects.length === 0 ? (
            <Card className="border border-dashed border-border bg-white">
              <CardContent className="p-12 text-center">
                <FolderKanban className="w-10 h-10 text-muted-foreground mx-auto mb-3" strokeWidth={1.5} />
                <p className="text-muted-foreground">No projects yet. Create your first project to get started.</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {recentProjects.map((project) => (
                <Card
                  key={project.id}
                  className="border border-border bg-white shadow-sm card-interactive cursor-pointer"
                  onClick={() => navigate(`/projects/${project.id}`)}
                  data-testid={`project-card-${project.id}`}
                >
                  <CardContent className="p-5">
                    <div className="flex items-start justify-between mb-3">
                      <h3 className="font-medium text-foreground truncate pr-2">{project.name}</h3>
                      <Badge
                        variant="secondary"
                        className={project.status === 'active' ? 'status-active' : 'status-paused'}
                        data-testid={`project-status-${project.id}`}
                      >
                        {project.status}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground font-mono mb-3" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                      /{project.slug}
                    </p>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <FileCode className="w-3.5 h-3.5" />{project.script_count || 0} scripts
                      </span>
                      <span className="flex items-center gap-1">
                        <Globe className="w-3.5 h-3.5" />{project.whitelist_count || 0} domains
                      </span>
                    </div>
                    {project.category && (
                      <Badge variant="outline" className="mt-3 text-xs">{project.category.name}</Badge>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
