import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  Check,
  ChevronRight,
  CloudUpload,
  Download,
  FileText,
  Fingerprint,
  GraduationCap,
  LayoutDashboard,
  LockKeyhole,
  LogOut,
  Mail,
  Menu,
  MessageSquareText,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
  X,
  Zap,
  UserCheck,
} from 'lucide-react';
import { supabase, supabaseConfigured } from './supabase';
import './style.css';

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const JD =
  'Software Development Engineer Intern. We need Python, React, REST APIs, SQL, Git and Docker. Candidate should understand data structures and problem solving, build reliable software, write tests, collaborate in an Agile team, communicate technical decisions and have exposure to cloud deployment.';

const demo = {
  role_title: 'Software Development Engineer Intern',
  summary: { total: 8, demonstrated: 3, partial: 2, missing: 3, readiness: 50 },
  disclaimer:
    'Not Evidenced means no proof was found in this resume, not that the person lacks the skill. This is decision support, not a hiring decision.',
  skills: [
    ['Python', 'demonstrated', 0.91, 'Built a Python automation tool to validate API responses and export structured JSON reports.'],
    ['React', 'demonstrated', 0.86, 'Developed a responsive React dashboard with reusable components and interactive charts.'],
    ['Git', 'demonstrated', 0.82, 'Maintained project source code on GitHub using feature branches and documented commits.'],
    ['REST APIs', 'partial', 0.48, 'Integrated external APIs into a student productivity dashboard.'],
    ['SQL', 'partial', 0.39, 'Worked with structured application data and database records.'],
    ['Docker', 'missing', 0, ''],
    ['Agile', 'missing', 0, ''],
    ['Cloud Computing', 'missing', 0, ''],
  ].map(([skill, status, confidence, snippet]) => ({
    skill,
    status,
    confidence,
    interpretation:
      status === 'missing'
        ? 'No reliable evidence was found in the supplied resume.'
        : status === 'partial'
        ? 'Related evidence was found, but depth needs clarification.'
        : 'Direct skill mention supported by an action-oriented resume statement.',
    evidence: snippet
      ? [{ snippet, signals: ['resume source anchor'], match: confidence }]
      : [],
    review_required: status !== 'demonstrated',
  })),
  action_plan: [
    {
      skill: 'Docker',
      title: 'Containerize a Small API',
      duration: '2 days',
      description:
        'Write a Dockerfile, build an image and document how to run an API with environment variables.',
      deliverables: ['Dockerfile', 'Image', 'Ports', 'Environment'],
    },
    {
      skill: 'Agile',
      title: 'Run a Mini Sprint',
      duration: '2 days',
      description:
        'Turn a small feature into user stories, prioritize tasks and document a two-day sprint review.',
      deliverables: ['User stories', 'Sprint board', 'Review notes'],
    },
    {
      skill: 'Cloud Computing',
      title: 'Deploy a Proof-of-Concept',
      duration: '2 days',
      description:
        'Deploy a small application and document architecture, configuration and limitations.',
      deliverables: ['Live demo', 'Architecture note', 'Deployment guide'],
    },
  ],
  interview_questions: [
    { skill: 'Python', question: 'How would you handle exceptions and validate external input?' },
    { skill: 'React', question: 'When would you use useEffect, and what causes repeated effects?' },
    { skill: 'REST APIs', question: 'How do HTTP methods and status codes shape a REST API?' },
    { skill: 'SQL', question: 'Explain INNER JOIN vs LEFT JOIN with an example.' },
  ],
};

function App() {
  const [token, setToken] = useState(localStorage.getItem('sp_token') || '');
  const [user, setUser] = useState(null);
  const [tab, setTab] = useState('overview');
  const [resume, setResume] = useState(null);
  const [jd, setJd] = useState(JD);
  const [role, setRole] = useState('Software Development Engineer Intern');
  const [result, setResult] = useState(demo);
  const [busy, setBusy] = useState(false);
  const [authBusy, setAuthBusy] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');
  const [authOpen, setAuthOpen] = useState(false);
  const [mode, setMode] = useState(supabaseConfigured ? 'login' : 'legacy_login'); // 'login' | 'register' | 'legacy_login' | 'link_account' | 'email_notice'
  const [noticeMessage, setNoticeMessage] = useState('');
  const [pendingSbToken, setPendingSbToken] = useState('');
  const [linkPassword, setLinkPassword] = useState('');
  const [form, setForm] = useState({ name: '', email: '', password: '', college: '' });
  const [expanded, setExpanded] = useState('Python');
  const [history, setHistory] = useState([]);
  const [collegeData, setCollegeData] = useState(null);
  const [mobile, setMobile] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [profileForm, setProfileForm] = useState({ name: '', college: '' });
  const [profileBusy, setProfileBusy] = useState(false);
  const [profileError, setProfileError] = useState('');

  const headers = token ? { Authorization: 'Bearer ' + token } : {};

  async function loadHistory(authToken = token) {
    if (!authToken) return;
    try {
      const r = await fetch(API + '/api/analyses', {
        headers: { Authorization: 'Bearer ' + authToken },
      });
      if (r.ok) {
        setHistory(await r.json());
      }
    } catch {}
  }

  // Restore or sync Supabase session on mount
  useEffect(() => {
    let mounted = true;

    async function checkExistingSession() {
      if (token) {
        try {
          const r = await fetch(API + '/api/auth/me', { headers });
          if (r.ok) {
            const data = await r.json();
            if (mounted) {
              setUser(data);
              loadHistory(token);
            }
          } else {
            // Token expired or invalid
            logout();
          }
        } catch {
          // If offline or failed, keep local token for potential reconnect
        }
      }

      if (supabase) {
        try {
          const { data: { session } } = await supabase.auth.getSession();
          if (session?.access_token && !token) {
            syncWithBackend(session.access_token);
          }
        } catch (err) {
          console.warn('Supabase getSession notice:', err);
        }
      }
    }

    checkExistingSession();

    let authSubscription;
    if (supabase) {
      const { data } = supabase.auth.onAuthStateChange(
        async (event, session) => {
          if (event === 'SIGNED_IN' && session?.access_token) {
            syncWithBackend(session.access_token);
          } else if (event === 'SIGNED_OUT') {
            // Only clear the session when there is no legacy JWT in storage.
            const legacyToken = localStorage.getItem('sp_token');
            if (!legacyToken) {
              logout();
            }
          }
        }
      );
      authSubscription = data.subscription;
    }

    return () => {
      mounted = false;
      authSubscription?.unsubscribe();
    };
  }, []);

  async function syncWithBackend(supabaseAccessToken, meta = {}) {
    setAuthBusy(true);
    setError('');
    try {
      const res = await fetch(API + '/api/auth/supabase/sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer ' + supabaseAccessToken,
        },
        body: JSON.stringify({
          name: meta.name || form.name || undefined,
          college: meta.college || form.college || undefined,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Authentication sync failed');
      }

      if (data.status === 'requires_linking') {
        setPendingSbToken(supabaseAccessToken);
        setMode('link_account');
        setNoticeMessage(data.message || 'Please link your existing SkillProof account.');
        setAuthBusy(false);
        return;
      }

      if (data.status === 'ready') {
        const appToken = data.access_token;
        localStorage.setItem('sp_token', appToken);
        setToken(appToken);
        setUser(data.user);
        setAuthOpen(false);
        setPendingSbToken('');
        setLinkPassword('');
        setToast(`Welcome back, ${data.user.name || 'Explorer'}!`);
        loadHistory(appToken);
      }
    } catch (err) {
      setError(err.message || 'Failed to authenticate with server');
    } finally {
      setAuthBusy(false);
    }
  }

  // Handle Account Linking with legacy password
  async function handleLinkAccount(e) {
    e.preventDefault();
    if (!linkPassword) {
      setError('Please enter your existing SkillProof password');
      return;
    }
    setAuthBusy(true);
    setError('');
    try {
      const res = await fetch(API + '/api/auth/supabase/link', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer ' + pendingSbToken,
        },
        body: JSON.stringify({ password: linkPassword }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Account linking failed');
      }

      const appToken = data.access_token;
      localStorage.setItem('sp_token', appToken);
      setToken(appToken);
      setUser(data.user);
      setAuthOpen(false);
      setPendingSbToken('');
      setLinkPassword('');
      setToast('SkillProof account securely linked with Supabase!');
      loadHistory(appToken);
    } catch (err) {
      setError(err.message);
    } finally {
      setAuthBusy(false);
    }
  }

  // Supabase Signup / Signin or Legacy Signin
  async function auth(e) {
    e.preventDefault();
    setError('');
    setAuthBusy(true);

    try {
      if (mode === 'legacy_login') {
        // Fallback classic HS256 authentication
        const r = await fetch(API + '/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: form.email, password: form.password }),
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.detail || 'Could not sign in');
        localStorage.setItem('sp_token', d.access_token);
        setToken(d.access_token);
        setUser(d.user);
        setAuthOpen(false);
        setToast('Your proof workspace is ready');
        loadHistory(d.access_token);
        return;
      }

      if (!supabase) {
        throw new Error(
          'Supabase authentication is not configured. Set the frontend Supabase variables or use legacy sign-in.'
        );
      }

      if (mode === 'register') {
        // Supabase Signup flow
        const { data, error: sbError } = await supabase.auth.signUp({
          email: form.email.trim(),
          password: form.password,
          options: {
            data: {
              full_name: form.name.trim(),
              college: form.college.trim(),
            },
          },
        });

        if (sbError) throw sbError;

        if (data?.session?.access_token) {
          // If auto-confirmed
          await syncWithBackend(data.session.access_token, {
            name: form.name.trim(),
            college: form.college.trim(),
          });
        } else {
          // Email confirmation required
          setMode('email_notice');
          setNoticeMessage(
            `A confirmation email has been sent to ${form.email}. Please verify your email before logging in to access saved analyses.`
          );
        }
      } else {
        // Supabase Login flow
        const { data, error: sbError } = await supabase.auth.signInWithPassword({
          email: form.email.trim(),
          password: form.password,
        });

        if (sbError) {
          // Helpful guidance if password failed or user has an unlinked legacy account
          throw sbError;
        }

        if (data?.session?.access_token) {
          await syncWithBackend(data.session.access_token);
        } else {
          throw new Error('No session returned. Please check email verification.');
        }
      }
    } catch (e) {
      const msg = e.message || '';
      if (
        msg.toLowerCase().includes('rate limit') ||
        msg.toLowerCase().includes('over_email_send_rate_limit')
      ) {
        setError(
          'Email verification limit reached on Supabase. If you cannot access email confirmation, switch to "Legacy Sign In" below to log in immediately with your password.'
        );
      } else if (
        msg.toLowerCase().includes('email not confirmed') ||
        msg.toLowerCase().includes('not confirmed')
      ) {
        setError(
          'Your email is not yet confirmed in Supabase. Please check your inbox or sign in using your local SkillProof password via "Legacy Sign In".'
        );
      } else if (
        msg.toLowerCase().includes('user already registered') ||
        msg.toLowerCase().includes('already registered')
      ) {
        setError(
          'This email is already registered. Please sign in instead, or use "Legacy Sign In" if you registered locally.'
        );
      } else if (
        msg.toLowerCase().includes('invalid login credentials') ||
        msg.toLowerCase().includes('invalid credentials')
      ) {
        setError(
          'Invalid email or password. If you have a legacy account, try "Use legacy local password".'
        );
      } else {
        setError(msg || 'Authentication failed. Please check your connection.');
      }
    } finally {
      setAuthBusy(false);
    }
  }

  async function analyse(e) {
    e.preventDefault();
    if (!resume) {
      setError('Please upload a PDF resume first.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      let f = new FormData();
      f.append('resume', resume);
      f.append('job_description', jd);
      f.append('role_title', role);
      let r = await fetch(API + '/api/analyze', {
        method: 'POST',
        headers,
        body: f,
      });
      let d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Analysis failed');
      setResult(d);
      setExpanded(d.skills?.[0]?.skill || '');
      setTab('evidence');
      if (token) loadHistory(token);
      setToast('Evidence map generated');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function loadCollege() {
    try {
      const r = await fetch(API + '/api/college/overview', { headers });
      if (r.ok) {
        setCollegeData(await r.json());
      } else {
        setToast('Sign in with a college account to view campus insights.');
      }
    } catch {
      setToast('Could not load college insights.');
    }
  }

  async function openHistory(id) {
    try {
      let r = await fetch(API + '/api/analyses/' + id, { headers });
      if (r.ok) {
        const data = await r.json();
        // Guarantee analysis_id is always set so exportPdf() can use it.
        // The backend now injects this, but we also guard here for safety.
        if (!data.analysis_id) data.analysis_id = id;
        setResult(data);
        setTab('evidence');
      }
    } catch {
      setToast('Could not load analysis details.');
    }
  }

  async function exportPdf() {
    if (result.analysis_id && token) {
      try {
        const r = await fetch(API + '/api/analyses/' + result.analysis_id + '/report', {
          headers,
        });
        if (!r.ok) throw new Error('Could not export report');
        const blob = await r.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `SkillProof_Action_Plan_${result.analysis_id}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
      } catch (e) {
        setToast(e.message);
      }
    } else {
      setToast('Sign in and run a new analysis to export its PDF report.');
    }
  }

  async function logout() {
    try {
      if (supabase) await supabase.auth.signOut();
    } catch {}
    localStorage.removeItem('sp_token');
    setToken('');
    setUser(null);
    setHistory([]);
    setPendingSbToken('');
  }

  function openEditProfile() {
    if (!user) return;
    setProfileForm({
      name: user.name || '',
      college: user.college || '',
    });
    setProfileError('');
    setProfileOpen(true);
  }

  async function handleUpdateProfile(e) {
    e.preventDefault();
    if (!profileForm.name.trim()) {
      setProfileError('Full name is required.');
      return;
    }
    setProfileBusy(true);
    setProfileError('');
    try {
      const res = await fetch(API + '/api/auth/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...headers,
        },
        body: JSON.stringify({
          name: profileForm.name.trim(),
          college: profileForm.college.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to update profile');
      }
      setUser(data);
      setProfileOpen(false);
      setToast('Profile updated successfully!');
      if (tab === 'college') {
        loadCollege();
      }
    } catch (err) {
      setProfileError(err.message || 'Error updating profile');
    } finally {
      setProfileBusy(false);
    }
  }

  const s = result.summary || demo.summary;
  const nav = [
    ['overview', 'Overview', LayoutDashboard],
    ['evidence', 'Evidence map', Fingerprint],
    ['roadmap', 'Action plan', Target],
    ['interview', 'Interview prep', MessageSquareText],
  ];
  const labels = {
    demonstrated: 'Demonstrated',
    partial: 'Partial support',
    missing: 'Not evidenced',
  };

  return (
    <div className="shell">
      <aside className={'sidebar ' + (mobile ? 'show' : '')}>
        <div className="brand">
          <div className="mark">
            <Fingerprint />
          </div>
          <div>
            <b>
              skillproof<span>.ai</span>
            </b>
            <small>CAREER INTELLIGENCE</small>
          </div>
          <button className="close" onClick={() => setMobile(false)}>
            <X />
          </button>
        </div>
        <div className="side-label">WORKSPACE</div>
        {nav.map(([id, name, I]) => (
          <button
            className={'nav ' + (tab === id ? 'active' : '')}
            key={id}
            onClick={() => {
              setTab(id);
              setMobile(false);
            }}
          >
            <I size={17} />
            {name}
            {id === 'evidence' && <small>{s.total}</small>}
          </button>
        ))}
        <div className="side-label gap">YOUR ACTIVITY</div>
        <button
          className={'nav ' + (tab === 'readiness' ? 'active' : '')}
          onClick={() => setTab('readiness')}
        >
          <BarChart3 size={17} />
          Readiness insights
        </button>
        <button
          className={'nav ' + (tab === 'college' ? 'active' : '')}
          onClick={() => {
            setTab('college');
            if (token) loadCollege();
            else setAuthOpen(true);
          }}
        >
          <GraduationCap size={17} />
          College insights <small>BETA</small>
        </button>
        <div className="side-bottom">
          <div className="promo">
            <Sparkles />
            <b>Proof compounds.</b>
            <p>Turn every project into a stronger career signal.</p>
            <button onClick={() => setTab('roadmap')}>Build your next proof ↗</button>
          </div>
          <div className="profile" style={{ cursor: user ? 'pointer' : 'default' }}>
            <div className="avatar" onClick={openEditProfile} title={user ? "Edit Profile" : ""}>
              {user?.name?.[0] || 'G'}
            </div>
            <div style={{ flex: 1, minWidth: 0 }} onClick={openEditProfile} title={user ? "Edit Profile" : ""}>
              <b style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                {user?.name || 'Guest explorer'}
                {user && <UserCheck size={13} style={{ color: '#10b981', flexShrink: 0 }} />}
              </b>
              <small>{user?.email || 'Demo workspace'}</small>
            </div>
            {user ? (
              <div style={{ display: 'flex', gap: '4px' }}>
                <button onClick={openEditProfile} title="Edit profile" style={{ padding: '6px' }}>
                  <UserCheck size={15} />
                </button>
                <button onClick={logout} title="Sign out" style={{ padding: '6px' }}>
                  <LogOut size={15} />
                </button>
              </div>
            ) : (
              <button onClick={() => setAuthOpen(true)} title="Sign in">
                <LockKeyhole size={16} />
              </button>
            )}
          </div>
        </div>
      </aside>

      {mobile && <div className="scrim" onClick={() => setMobile(false)} />}

      <main>
        <header>
          <div className="crumb">
            <button className="hamb" onClick={() => setMobile(true)}>
              <Menu />
            </button>
            Workspace <ChevronRight size={13} />
            <b>
              {nav.find((n) => n[0] === tab)?.[1] ||
                (tab === 'readiness' ? 'Readiness insights' : 'College insights')}
            </b>
          </div>
          <div className="topright">
            <i /> EVIDENCE ENGINE ONLINE{' '}
            {user ? (
              <button onClick={logout} title="Click to sign out">
                {user.name.split(' ')[0]} ↗
              </button>
            ) : (
              <button onClick={() => setAuthOpen(true)}>Sign in ↗</button>
            )}
          </div>
        </header>

        <div className="content">
          <div className="pagehead">
            <div>
              <div className="eyebrow">✳ &nbsp; YOUR CAREER, WITH RECEIPTS</div>
              <h1>
                {tab === 'overview'
                  ? 'Make your skills undeniable.'
                  : tab === 'evidence'
                  ? 'Your evidence, decoded.'
                  : tab === 'roadmap'
                  ? 'Build proof. Close gaps.'
                  : tab === 'readiness'
                  ? 'Your readiness, at a glance.'
                  : tab === 'college'
                  ? 'Campus skill intelligence.'
                  : 'Walk into interviews prepared.'}
              </h1>
              <p>
                {tab === 'overview'
                  ? 'A clearer view of what you can prove — and what to build next.'
                  : 'Every next step grounded in the requirements of your target role.'}
              </p>
            </div>
            <div className="head-actions">
              <span className="rolechip">▣ &nbsp;{role}</span>
              <button className="secondary" onClick={() => setTab('overview')}>
                <Plus size={14} /> New analysis
              </button>
            </div>
          </div>

          {error && (
            <div className="error">
              {error}
              <button onClick={() => setError('')}>×</button>
            </div>
          )}

          {tab === 'overview' && (
            <div className="columns">
              <section>
                <div className="panel upload">
                  <div className="panelhead">
                    <div>
                      <div className="eyebrow">01 / START WITH YOUR CONTEXT</div>
                      <h2>Build your evidence map</h2>
                      <p>One resume. One role. A much clearer next step.</p>
                    </div>
                    <CloudUpload size={28} />
                  </div>
                  <form onSubmit={analyse}>
                    <label>TARGET ROLE</label>
                    <input value={role} onChange={(e) => setRole(e.target.value)} />
                    <label>
                      YOUR RESUME <small>PDF · MAX 8 MB</small>
                    </label>
                    <label className="drop">
                      <input
                        type="file"
                        accept=".pdf,application/pdf"
                        onChange={(e) => setResume(e.target.files[0])}
                      />
                      <CloudUpload />
                      <span>
                        <b>{resume?.name || 'Drop your resume here'}</b>
                        <small>
                          {resume ? 'Ready to analyse · PDF selected' : 'or click to browse files'}
                        </small>
                      </span>
                      <em>Browse</em>
                    </label>
                    <label>
                      JOB DESCRIPTION <small>PASTE ROLE REQUIREMENTS</small>
                    </label>
                    <textarea value={jd} onChange={(e) => setJd(e.target.value)} />
                    <div className="formfoot">
                      <span>
                        <ShieldCheck size={14} /> Resume processed in memory
                      </span>
                      <button className="primary" disabled={busy}>
                        {busy ? 'Mapping evidence…' : 'Build my evidence map ↗'}
                      </button>
                    </div>
                  </form>
                </div>
                <div className="steps">
                  <span>
                    <i>01</i>
                    <b>Parse</b>
                    <small>Resume + role</small>
                  </span>
                  →
                  <span>
                    <i>02</i>
                    <b>Ground</b>
                    <small>Find evidence</small>
                  </span>
                  →
                  <span>
                    <i>03</i>
                    <b>Prove</b>
                    <small>Map & improve</small>
                  </span>
                </div>
              </section>

              <section className="right">
                <div className="panel snapshot">
                  <div className="snapshot-head">
                    CAREER READINESS SNAPSHOT <small>● LIVE MAP</small>
                  </div>
                  <div className="score">
                    <div>
                      <strong>
                        {s.readiness}
                        <small>%</small>
                      </strong>
                      <b>Evidence coverage</b>
                      <p>Weighted signal across role requirements</p>
                    </div>
                    <div className="donut" style={{ '--pct': s.readiness * 3.6 + 'deg' }}>
                      <span>
                        ◉
                        <b>
                          {s.readiness >= 75 ? 'Strong' : s.readiness >= 45 ? 'Building' : 'Early'}
                        </b>
                      </span>
                    </div>
                  </div>
                  {[
                    ['Demonstrated', s.demonstrated, 'green'],
                    ['Partial support', s.partial, 'yellow'],
                    ['Not evidenced', s.missing, 'red'],
                  ].map(([n, v, c]) => (
                    <div className="metric" key={n}>
                      <i className={c} />
                      {n}
                      <b>{v}</b>
                    </div>
                  ))}
                  <button className="link" onClick={() => setTab('evidence')}>
                    Explore evidence map ↗
                  </button>
                </div>

                <div className="panel insight">
                  <Zap />
                  <div>
                    <div className="eyebrow">THE IMPORTANT DISTINCTION</div>
                    <h3>No evidence ≠ no ability.</h3>
                    <p>A gap is a prompt to add stronger evidence — not a verdict on your potential.</p>
                  </div>
                </div>

                <div className="panel recent">
                  <div className="row">
                    <div>
                      <div className="eyebrow">RECENT WORK</div>
                      <h3>Your analyses</h3>
                    </div>
                    {user ? (
                      <button className="link" onClick={() => loadHistory(token)}>
                        Refresh ↻
                      </button>
                    ) : (
                      <button className="link" onClick={() => setAuthOpen(true)}>
                        Sign in ↗
                      </button>
                    )}
                  </div>
                  {history.length ? (
                    history.slice(0, 4).map((h) => (
                      <button className="history" key={h.id} onClick={() => openHistory(h.id)}>
                        <FileText />
                        <span>
                          <b>{h.role_title}</b>
                          <small>{h.resume_name}</small>
                        </span>
                        <strong>{h.summary?.readiness}%</strong>
                      </button>
                    ))
                  ) : (
                    <p className="muted">
                      {token
                        ? 'No saved analyses yet. Build an evidence map above!'
                        : 'Sign in to save and revisit evidence maps.'}
                    </p>
                  )}
                </div>
              </section>
            </div>
          )}

          {tab === 'evidence' && (
            <>
              <div className="evidence-top">
                <div className="panel coverage">
                  <div className="eyebrow">ROLE EVIDENCE COVERAGE</div>
                  <strong>{s.readiness}%</strong>
                  <p>
                    {s.demonstrated} of {s.total} requirements directly demonstrated
                  </p>
                  <div className="bar">
                    <i
                      style={{
                        width: (s.demonstrated / Math.max(1, s.total)) * 100 + '%',
                      }}
                    />
                    <i
                      style={{
                        width: (s.partial / Math.max(1, s.total)) * 100 + '%',
                      }}
                    />
                    <i
                      style={{
                        width: (s.missing / Math.max(1, s.total)) * 100 + '%',
                      }}
                    />
                  </div>
                </div>
                <div className="panel legend">
                  {[
                    ['Demonstrated', s.demonstrated, 'green'],
                    ['Partial support', s.partial, 'yellow'],
                    ['Not evidenced', s.missing, 'red'],
                  ].map(([n, v, c]) => (
                    <div key={n}>
                      <i className={c} />
                      {n}
                      <b>{v}</b>
                    </div>
                  ))}
                  <small>Classification is based on evidence in the supplied resume.</small>
                </div>
              </div>

              <div className="section-title">
                <div>
                  <div className="eyebrow">REQUIREMENT-BY-REQUIREMENT</div>
                  <h2>
                    Skill evidence map <small>{s.total} SKILLS</small>
                  </h2>
                </div>
                <button className="secondary" onClick={exportPdf}>
                  <Download size={14} /> Export report
                </button>
              </div>

              <div className="skilllist">
                {result.skills.map((x) => (
                  <div className="skill" key={x.skill}>
                    <button
                      className="skillhead"
                      onClick={() => setExpanded(expanded === x.skill ? '' : x.skill)}
                    >
                      <span className={'status ' + x.status}>
                        {x.status === 'demonstrated' ? (
                          <Check />
                        ) : x.status === 'partial' ? (
                          <Activity />
                        ) : (
                          <Search />
                        )}
                      </span>
                      <span className="skillname">
                        <b>{x.skill}</b>
                        <small>{labels[x.status]}</small>
                      </span>
                      <span className="confidence">
                        <small>Evidence signal</small>
                        <b>{Math.round(x.confidence * 100)}%</b>
                      </span>
                      <span className="track">
                        <i style={{ width: x.confidence * 100 + '%' }} />
                      </span>
                      <ChevronRight />
                    </button>
                    {expanded === x.skill && (
                      <div className="detail">
                        <p>{x.interpretation}</p>
                        {x.evidence.length ? (
                          <>
                            <div className="eyebrow">⌁ &nbsp; SOURCE ANCHORS FROM RESUME</div>
                            {x.evidence.map((e, i) => (
                              <blockquote key={i}>
                                “{e.snippet}”
                                <small>{e.signals.join(' · ')}</small>
                              </blockquote>
                            ))}
                          </>
                        ) : (
                          <div className="noanchor">
                            No reliable resume anchor found. If you have this skill, add a concrete
                            project, action and outcome to your resume.
                          </div>
                        )}
                        {x.review_required && (
                          <small className="review">
                            ◎ Human review recommended — verify this match.
                          </small>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
              <p className="disclaimer">{result.disclaimer}</p>
            </>
          )}

          {tab === 'readiness' && (
            <>
              <div className="evidence-top">
                <div className="panel coverage">
                  <div className="eyebrow">ROLE READINESS SCORE</div>
                  <strong>{s.readiness}%</strong>
                  <p>
                    {s.demonstrated} of {s.total} requirements directly demonstrated
                  </p>
                  <div className="bar">
                    <i
                      style={{
                        width: (s.demonstrated / Math.max(1, s.total)) * 100 + '%',
                      }}
                    />
                    <i
                      style={{
                        width: (s.partial / Math.max(1, s.total)) * 100 + '%',
                      }}
                    />
                    <i
                      style={{
                        width: (s.missing / Math.max(1, s.total)) * 100 + '%',
                      }}
                    />
                  </div>
                </div>
                <div className="panel legend">
                  {[
                    ['Demonstrated', s.demonstrated, 'green'],
                    ['Partial support', s.partial, 'yellow'],
                    ['Not evidenced', s.missing, 'red'],
                  ].map(([n, v, c]) => (
                    <div key={n}>
                      <i className={c} />
                      {n}
                      <b>{v}</b>
                    </div>
                  ))}
                  <small>Based on evidence found in your current resume analysis.</small>
                </div>
              </div>

              <div className="section-title">
                <div>
                  <div className="eyebrow">SKILL-LEVEL BREAKDOWN</div>
                  <h2>Skills to strengthen</h2>
                </div>
                <button className="secondary" onClick={() => setTab('evidence')}>
                  View evidence map ↗
                </button>
              </div>

              <div className="projects">
                {result.skills
                  .filter((x) => x.status !== 'demonstrated')
                  .map((x) => (
                    <div className="panel project" key={x.skill}>
                      <small>{labels[x.status]}</small>
                      <em>{Math.round(x.confidence * 100)}% evidence signal</em>
                      <h3>{x.skill}</h3>
                      <p>{x.interpretation}</p>
                      <p className="muted">
                        {x.evidence.length
                          ? x.evidence.length + ' resume evidence anchor(s) found.'
                          : 'Add a concrete project, action and outcome to your resume.'}
                      </p>
                    </div>
                  ))}
              </div>

              <div className="section-title">
                <div>
                  <div className="eyebrow">YOUR NEXT MOVES</div>
                  <h2>Recommended action sprints</h2>
                </div>
                <button className="secondary" onClick={() => setTab('roadmap')}>
                  Open action plan ↗
                </button>
              </div>

              <div className="projects">
                {result.action_plan.slice(0, 3).map((x, i) => (
                  <div className="panel project" key={x.skill}>
                    <small>
                      SPRINT 0{i + 1} · {x.duration}
                    </small>
                    <em>{x.skill}</em>
                    <h3>{x.title}</h3>
                    <p>{x.description}</p>
                  </div>
                ))}
              </div>
            </>
          )}

          {tab === 'roadmap' && (
            <>
              <div className="panel intro">
                <Target />
                <div>
                  <div className="eyebrow">YOUR NEXT PROOF MOVES</div>
                  <h2>Turn gaps into portfolio evidence.</h2>
                  <p>
                    Finish a focused sprint, document the artifact, then add it to your portfolio.
                  </p>
                </div>
              </div>
              <div className="projects">
                {result.action_plan.map((p, i) => (
                  <div className="panel project" key={p.skill}>
                    <small>
                      SPRINT 0{i + 1} · ⚡ {p.duration}
                    </small>
                    <em>{p.skill}</em>
                    <h3>{p.title}</h3>
                    <p>{p.description}</p>
                    <div className="checklist">
                      <b>PROOF CHECKLIST</b>
                      {p.deliverables.map((d) => (
                        <span key={d}>✓ {d}</span>
                      ))}
                    </div>
                    <button
                      className="link"
                      onClick={() =>
                        setToast('Build the artifact, document it and rerun your evidence map.')
                      }
                    >
                      Start this sprint ↗
                    </button>
                  </div>
                ))}
              </div>
            </>
          )}

          {tab === 'college' && (
            <>
              <div className="panel intro">
                <GraduationCap />
                <div>
                  <div className="eyebrow">CAMPUS INTELLIGENCE · BETA</div>
                  <h2>Make skill gaps visible at cohort level.</h2>
                  <p>
                    Aggregate evidence signals from analyses saved by students in the same college
                    workspace.
                  </p>
                </div>
                <button className="secondary" onClick={loadCollege}>
                  Refresh
                </button>
              </div>
              {collegeData && collegeData.college ? (
                <>
                  <div className="evidence-top">
                    <div className="panel coverage">
                      <div className="eyebrow">SAVED ANALYSES</div>
                      <strong>{collegeData.analyses}</strong>
                      <p>{collegeData.college}</p>
                    </div>
                    <div className="panel legend">
                      {[
                        ['Demonstrated', collegeData.evidence_totals.demonstrated, 'green'],
                        ['Partial support', collegeData.evidence_totals.partial, 'yellow'],
                        ['Not evidenced', collegeData.evidence_totals.missing, 'red'],
                      ].map(([n, v, c]) => (
                        <div key={n}>
                          <i className={c} />
                          {n}
                          <b>{v}</b>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="panel coverage">
                    <div className="eyebrow">MOST FREQUENT EVIDENCE GAPS</div>
                    {collegeData.top_skill_gaps.map((x) => (
                      <div className="metric" key={x.skill}>
                        {x.skill}
                        <b>{x.missing} not evidenced</b>
                      </div>
                    ))}
                    <p className="muted">{collegeData.note}</p>
                  </div>
                </>
              ) : (
                <div className="panel coverage">
                  <p className="muted">
                    Sign in and specify your college or university in your profile to view
                    cohort-level evidence signals.
                  </p>
                  <button className="primary" onClick={() => setAuthOpen(true)}>
                    Sign in / Create account
                  </button>
                </div>
              )}
            </>
          )}

          {tab === 'interview' && (
            <>
              <div className="panel intro">
                <MessageSquareText />
                <div>
                  <div className="eyebrow">ROLE-SPECIFIC PRACTICE</div>
                  <h2>Prepare with your evidence in mind.</h2>
                  <p>
                    Connect technical knowledge to a real project, decision or measurable outcome.
                  </p>
                </div>
              </div>
              <div className="questions">
                {result.interview_questions.map((q, i) => (
                  <div className="panel question" key={i}>
                    <small>Q{i + 1}</small>
                    <div>
                      <em>{q.skill}</em>
                      <h3>{q.question}</h3>
                      <p>Structure: context → action → technical decision → result → learning.</p>
                    </div>
                    <button onClick={() => navigator.clipboard?.writeText(q.question)}>
                      Copy
                    </button>
                  </div>
                ))}
              </div>
            </>
          )}

          <footer>
            © 2026 SKILLPROOF AI · TEAM NOVARYTHM{' '}
            <span>PROOF OVER KEYWORDS ✳ BUILT FOR HUMAN POTENTIAL</span>
          </footer>
        </div>
      </main>

      {authOpen && (
        <div className="overlay" onClick={() => setAuthOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <button className="x" onClick={() => setAuthOpen(false)}>
              ×
            </button>
            <div className="mark">
              <Fingerprint />
            </div>

            {mode === 'email_notice' ? (
              <div>
                <div className="eyebrow">EMAIL CONFIRMATION</div>
                <h2>Check your inbox</h2>
                <p style={{ marginTop: '10px', lineHeight: 1.6 }}>{noticeMessage}</p>
                <div style={{ marginTop: '20px' }}>
                  <button
                    className="primary"
                    style={{ width: '100%' }}
                    onClick={() => setMode('login')}
                  >
                    Return to sign in ↗
                  </button>
                </div>
              </div>
            ) : mode === 'link_account' ? (
              <div>
                <div className="eyebrow">EXISTING ACCOUNT VERIFICATION</div>
                <h2>Link your SkillProof Account</h2>
                <p style={{ marginTop: '8px', lineHeight: 1.6 }}>
                  An existing SkillProof account was found for your email. To protect your analysis
                  history and preserve your records, please verify your existing SkillProof
                  password.
                </p>
                <form onSubmit={handleLinkAccount}>
                  <label>EXISTING SKILLPROOF PASSWORD</label>
                  <input
                    type="password"
                    required
                    placeholder="Enter your existing SkillProof password"
                    value={linkPassword}
                    onChange={(e) => setLinkPassword(e.target.value)}
                  />
                  {error && <p className="error">{error}</p>}
                  <button className="primary" disabled={authBusy} style={{ marginTop: '16px' }}>
                    {authBusy ? 'Verifying & Linking…' : 'Verify & Link Account ↗'}
                  </button>
                </form>
                <p className="switch">
                  <button onClick={() => { setPendingSbToken(''); setMode('login'); }}>
                    Cancel and return to login
                  </button>
                </p>
              </div>
            ) : (
              <div>
                <div className="eyebrow">YOUR PROOF WORKSPACE</div>
                <h2>
                  {mode === 'login'
                    ? 'Welcome back.'
                    : mode === 'legacy_login'
                    ? 'Legacy SkillProof Sign in'
                    : 'Create your workspace.'}
                </h2>
                <p>
                  {mode === 'legacy_login'
                    ? 'Sign in directly with your original SkillProof credentials.'
                    : supabaseConfigured
                    ? 'Save analyses and revisit your evidence maps.'
                    : 'Supabase authentication is not configured. Use legacy sign-in or add the frontend Supabase settings.'}
                </p>

                <form onSubmit={auth}>
                  {mode === 'register' && (
                    <>
                      <label>FULL NAME</label>
                      <input
                        required
                        placeholder="e.g. Alex Johnson"
                        value={form.name}
                        onChange={(e) => setForm({ ...form, name: e.target.value })}
                      />
                      <label>COLLEGE / INSTITUTION</label>
                      <input
                        placeholder="e.g. Stanford University"
                        value={form.college}
                        onChange={(e) => setForm({ ...form, college: e.target.value })}
                      />
                    </>
                  )}
                  <label>EMAIL</label>
                  <input
                    type="email"
                    required
                    placeholder="name@example.com"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                  />
                  <label>PASSWORD</label>
                  <input
                    type="password"
                    minLength="8"
                    required
                    placeholder="At least 8 characters"
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                  />
                  {error && <p className="error">{error}</p>}
                  <button className="primary" disabled={authBusy} style={{ marginTop: '16px' }}>
                    {authBusy
                      ? 'Processing…'
                      : mode === 'login'
                      ? 'Sign in with Supabase ↗'
                      : mode === 'legacy_login'
                      ? 'Sign in with SkillProof ↗'
                      : 'Create account ↗'}
                  </button>
                </form>

                <p className="switch">
                  {mode === 'login' ? (
                    <>
                      New to SkillProof?{' '}
                      <button onClick={() => { setMode('register'); setError(''); }}>
                        Create account
                      </button>
                      <br />
                      <button
                        style={{ marginTop: '8px', opacity: 0.8 }}
                        onClick={() => { setMode('legacy_login'); setError(''); }}
                      >
                        Use legacy local password
                      </button>
                    </>
                  ) : mode === 'legacy_login' ? (
                    supabaseConfigured ? (
                      <>
                        Want to use Supabase?{' '}
                        <button onClick={() => { setMode('login'); setError(''); }}>
                          Supabase sign in
                        </button>
                      </>
                    ) : (
                      'Supabase sign-in is unavailable until its frontend environment variables are set.'
                    )
                  ) : (
                    <>
                      Already registered?{' '}
                      <button onClick={() => { setMode('login'); setError(''); }}>
                        Sign in
                      </button>
                    </>
                  )}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {profileOpen && (
        <div className="overlay" onClick={() => setProfileOpen(false)}>
          <div
            className="modal"
            onClick={(e) => e.stopPropagation()}
            style={{ width: 'min(480px, calc(100vw - 32px))', maxWidth: '480px' }}
          >
            <div className="modal-head">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <UserCheck size={18} style={{ color: '#10b981' }} />
                <h3 style={{ margin: 0 }}>Edit Profile</h3>
              </div>
              <button
                type="button"
                onClick={() => setProfileOpen(false)}
                style={{
                  background: 'none',
                  border: 0,
                  color: '#91a69a',
                  cursor: 'pointer',
                  padding: '4px',
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleUpdateProfile} style={{ marginTop: '16px' }}>
              <label>FULL NAME</label>
              <input
                type="text"
                required
                minLength="2"
                maxLength="80"
                placeholder="Your full name"
                value={profileForm.name}
                onChange={(e) =>
                  setProfileForm({ ...profileForm, name: e.target.value })
                }
              />

              <label style={{ marginTop: '12px', display: 'block' }}>
                COLLEGE / INSTITUTION
              </label>
              <input
                type="text"
                maxLength="120"
                placeholder="e.g. Stanford University, ABC College"
                value={profileForm.college}
                onChange={(e) =>
                  setProfileForm({ ...profileForm, college: e.target.value })
                }
              />
              <small style={{ color: '#94a3b8', fontSize: '11px', display: 'block', marginTop: '4px' }}>
                Setting your college enables aggregated campus insights in the College Insights tab.
              </small>

              {profileError && (
                <p className="error" style={{ marginTop: '12px' }}>
                  {profileError}
                </p>
              )}

              <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
                <button
                  type="button"
                  onClick={() => setProfileOpen(false)}
                  style={{
                    flex: 1,
                    background: '#1e293b',
                    color: '#f8fafc',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    padding: '10px',
                    cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="primary"
                  disabled={profileBusy}
                  style={{ flex: 1 }}
                >
                  {profileBusy ? 'Saving…' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {toast && (
        <div className="toast">
          <Check size={15} />
          {toast}
          <button onClick={() => setToast('')}>×</button>
        </div>
      )}
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
