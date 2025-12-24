'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';

const UserInfoPage = () => {
  const [userInfo, setUserInfo] = useState(null);

  const getUserInfo = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/users/info`, {
        method: 'GET',
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        setUserInfo(data);
      } else {
        console.error('エラーが発生しました');
      }
    } catch (err) {
      console.error('エラーが発生しました', err);
    }
  };

  useEffect(() => {
    getUserInfo();
  }, []);

  if (!userInfo) return <p className="text-center text-gray-500">読み込み中...</p>;

  return (
    <div className="min-h-screen bg-orange-100 flex items-center justify-center p-4">
      <div className="bg-white shadow-lg rounded-lg p-8 w-full max-w-lg">
        <h1 className="text-3xl font-bold text-center text-orange-600 mb-6">ユーザー情報</h1>
        <ul className="text-gray-700 text-left space-y-4">
          <li><strong>名前（漢字）:</strong> {userInfo.last_name_kanji} {userInfo.first_name_kanji}</li>
          <li><strong>名前（カナ）:</strong> {userInfo.last_name_kana} {userInfo.first_name_kana}</li>
          <li><strong>電話番号:</strong> {userInfo.phone_number}</li>
          <li><strong>郵便番号:</strong> {userInfo.postal_code}</li>
          <li><strong>住所:</strong> {userInfo.prefecture} {userInfo.city_address} {userInfo.detailed_address}</li>
          <li><strong>メールアドレス:</strong> {userInfo.email}</li>
          <li><strong>適格事業者:</strong> {userInfo.invoicing === 'yes' ? 'あり' : 'なし'}</li>
          {userInfo.invoicing === 'yes' &&
            <li><strong>適格事業者の番号:</strong> T{userInfo.invoicing_number}</li>}
          <li><strong>性別:</strong> {userInfo.gender === 'male' ? '男性' : '女性'}</li>
          <li><strong>職業:</strong> {userInfo.job}</li>
          <li><strong>誕生日:</strong> {userInfo.birth_date}</li>
          <li><strong>利用規約同意:</strong> {userInfo.agree ? 'あり' : 'なし'}</li>
          <li className="mt-6 font-bold text-xl text-orange-600">銀行情報</li>
          <li><strong>銀行名:</strong> {userInfo.bank_name || '未登録'}</li>
          <li><strong>支店名:</strong> {userInfo.branch_name || '未登録'}</li>
          <li><strong>口座種別:</strong> {userInfo.account_type || '未登録'}</li>
          <li><strong>口座番号:</strong> {userInfo.account_number || '未登録'}</li>
          <li><strong>口座名義:</strong> {userInfo.account_holder || '未登録'}</li>
        </ul>
        <h1 className="text-3xl font-bold text-center text-orange-600 mb-6">情報編集</h1>
        <Link href="/users/change" passHref>
          <span className="block text-orange-600 hover:text-orange-900 rounded-md py-2 px-2">◆ユーザー情報の編集</span>
        </Link>
        <Link href="/users/change-pass" passHref>
          <span className="block text-orange-600 hover:text-orange-900 rounded-md py-2 px-2">◆パスワードの編集</span>
        </Link>
      </div>
    </div>
  );
};

export default UserInfoPage;
