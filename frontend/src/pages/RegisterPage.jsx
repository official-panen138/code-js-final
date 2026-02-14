import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Code2, ArrowRight } from 'lucide-react';
import { toast } from 'sonner';

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password || !confirmPassword) {
      toast.error('Please fill in all fields');
      return;
    }
    if (password !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    if (password.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }
    setLoading(true);
    try {
      await register(email, password);
      toast.success('Account created successfully!');
      navigate('/dashboard');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex" data-testid="register-page">
      {/* Left panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-[#0F172A] flex-col justify-between p-12">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-md bg-white/10 flex items-center justify-center">
            <Code2 className="w-5 h-5 text-white" strokeWidth={2} />
          </div>
          <span className="text-xl font-semibold text-white tracking-tight" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
            JSHost
          </span>
        </div>
        <div>
          <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight leading-tight mb-6" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
            Start hosting your<br />scripts today.
          </h1>
          <p className="text-lg text-slate-400 leading-relaxed max-w-md">
            Create projects, add scripts, configure domain whitelists, and deliver JS securely to your websites.
          </p>
        </div>
        <p className="text-sm text-slate-500">Free to get started. No credit card required.</p>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-3 mb-10">
            <div className="w-9 h-9 rounded-md bg-[#0F172A] flex items-center justify-center">
              <Code2 className="w-4 h-4 text-white" strokeWidth={2} />
            </div>
            <span className="text-lg font-semibold tracking-tight" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>JSHost</span>
          </div>

          <Card className="border-0 shadow-none">
            <CardHeader className="px-0 pt-0">
              <CardTitle className="text-2xl font-semibold tracking-tight" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
                Create account
              </CardTitle>
              <CardDescription className="text-muted-foreground">
                Set up your JSHost account in seconds
              </CardDescription>
            </CardHeader>
            <CardContent className="px-0">
              <form onSubmit={handleSubmit} className="space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="email" className="label-caps">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    data-testid="register-email-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password" className="label-caps">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="Min 6 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    data-testid="register-password-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirm" className="label-caps">Confirm Password</Label>
                  <Input
                    id="confirm"
                    type="password"
                    placeholder="Confirm your password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    data-testid="register-confirm-input"
                  />
                </div>
                <Button
                  type="submit"
                  className="w-full bg-[#0F172A] hover:bg-[#1E293B] text-white rounded-md py-2.5 font-medium active:scale-95 transition-transform"
                  disabled={loading}
                  data-testid="register-submit-btn"
                >
                  {loading ? 'Creating account...' : 'Create account'}
                  {!loading && <ArrowRight className="w-4 h-4 ml-2" />}
                </Button>
              </form>
              <p className="mt-6 text-sm text-center text-muted-foreground">
                Already have an account?{' '}
                <Link to="/login" className="text-[#2563EB] font-medium hover:underline" data-testid="goto-login-link">
                  Sign in
                </Link>
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
