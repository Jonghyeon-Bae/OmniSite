import React from 'react';

export default function AdminUserTab({ users, onSelectUser }) {
  return (
    <div className="p-4 bg-gray-900 rounded-lg border border-gray-800">
      <h3 className="text-sm font-semibold text-gray-200 mb-3">👤 사용자 및 권한 관리</h3>
      <table className="w-full text-left text-xs text-gray-400">
        <thead className="bg-gray-800 text-gray-300">
          <tr>
            <th className="p-2">ID</th>
            <th className="p-2">계정명</th>
            <th className="p-2">권한</th>
          </tr>
        </thead>
        <tbody>
          {(users || []).map((u) => (
            <tr key={u.id} className="border-b border-gray-800 hover:bg-gray-800/50 cursor-pointer" onClick={() => onSelectUser && onSelectUser(u)}>
              <td className="p-2">{u.id}</td>
              <td className="p-2 font-medium text-gray-200">{u.username}</td>
              <td className="p-2 text-blue-400">{u.role || 'admin'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}