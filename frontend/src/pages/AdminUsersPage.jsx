import React, { useEffect, useState } from 'react';
import { apiClient } from '../services/api';

export default function AdminUsersPage() {
  const [users, setUsers] = useState([]);
  const [msg, setMsg] = useState('');
  const [newUser, setNewUser] = useState({
    email: '',
    full_name: '',
    password: '',
    role: 'executive',
    phone: '',
    department: 'Healthcare & Real Estate Advisory',
  });

  const loadUsers = async () => {
    try {
      const res = await apiClient.getUsers();
      setUsers(res.data || []);
    } catch (err) {
      setMsg(`Error: ${err.message}`);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setMsg('');
    try {
      await apiClient.createUser(newUser);
      setMsg(`Created user ${newUser.email}.`);
      setNewUser({
        email: '',
        full_name: '',
        password: '',
        role: 'executive',
        phone: '',
        department: 'Healthcare & Real Estate Advisory',
      });
      await loadUsers();
    } catch (err) {
      setMsg(`Error: ${err.message}`);
    }
  };

  const handleToggleActive = async (u) => {
    try {
      await apiClient.updateUser(u.id, { is_active: !u.is_active });
      await loadUsers();
    } catch (err) {
      setMsg(`Error: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div>
          <h2 className="text-base font-bold text-slate-900">
            Admin Users &amp; Executive Team (Role-Based Access Control)
          </h2>
          <p className="text-xs text-slate-500">
            Manage Administrators, Managers, and Lead Advisory Executives for automatic campaign lead assignment
          </p>
        </div>

        {msg && (
          <div className="p-3 rounded-lg bg-sky-50 border border-sky-200 text-sky-900 text-xs font-medium">
            {msg}
          </div>
        )}

        <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs">
          <input
            type="text"
            placeholder="Full Name"
            value={newUser.full_name}
            onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })}
            className="px-3 py-2 border border-slate-300 rounded-lg"
            required
          />
          <input
            type="email"
            placeholder="Email Address"
            value={newUser.email}
            onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
            className="px-3 py-2 border border-slate-300 rounded-lg"
            required
          />
          <input
            type="password"
            placeholder="Initial Password"
            value={newUser.password}
            onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
            className="px-3 py-2 border border-slate-300 rounded-lg"
            required
          />
          <select
            value={newUser.role}
            onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
            className="px-3 py-2 border border-slate-300 rounded-lg"
          >
            <option value="executive">Executive</option>
            <option value="manager">Manager</option>
            <option value="admin">Admin</option>
          </select>
          <input
            type="text"
            placeholder="Department"
            value={newUser.department}
            onChange={(e) => setNewUser({ ...newUser, department: e.target.value })}
            className="px-3 py-2 border border-slate-300 rounded-lg"
          />
          <button
            type="submit"
            className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg font-semibold"
          >
            + Add User
          </button>
        </form>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
            <tr>
              <th className="px-4 py-3">Full Name</th>
              <th className="px-4 py-3">Email</th>
              <th className="px-4 py-3">Role</th>
              <th className="px-4 py-3">Department</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {users.map((u) => (
              <tr key={u.id}>
                <td className="px-4 py-3 font-semibold text-slate-900">{u.full_name}</td>
                <td className="px-4 py-3 font-mono text-slate-600">{u.email}</td>
                <td className="px-4 py-3 uppercase font-semibold text-sky-700">{u.role}</td>
                <td className="px-4 py-3 text-slate-600">{u.department}</td>
                <td className="px-4 py-3">
                  <span
                    className={`px-2 py-0.5 rounded font-semibold ${
                      u.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                    }`}
                  >
                    {u.is_active ? 'Active' : 'Disabled'}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => handleToggleActive(u)}
                    className="px-2.5 py-1 rounded border border-slate-300 text-slate-700"
                  >
                    {u.is_active ? 'Disable' : 'Enable'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
