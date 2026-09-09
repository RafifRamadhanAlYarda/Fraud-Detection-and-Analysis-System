-- FRAUD DETECTION ANALYSIS SYSTEM (FDAS) - Bank BRI
-- Database Export for MySQL Import

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

-- --------------------------------------------------------
-- 1. Table structure for table `users`
-- --------------------------------------------------------

CREATE TABLE IF NOT EXISTS `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `fullname` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `user_id` varchar(100) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 2. Table structure for table `transaction_dictionary`
-- --------------------------------------------------------

CREATE TABLE IF NOT EXISTS `transaction_dictionary` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `grup` varchar(100) DEFAULT NULL,
  `jenis_transaksi` varchar(255) DEFAULT NULL,
  `deskripsi` text DEFAULT NULL,
  `keterangan_remark` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 3. Table structure for table `cleansing_history`
-- --------------------------------------------------------

CREATE TABLE IF NOT EXISTS `cleansing_history` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` varchar(100) NOT NULL,
  `filename` varchar(255) NOT NULL,
  `total_rows` int(11) DEFAULT NULL,
  `total_accounts` int(11) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 4. Table structure for table `fraud_result`
-- --------------------------------------------------------

CREATE TABLE IF NOT EXISTS `fraud_result` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `cleansing_id` int(11) DEFAULT NULL,
  `account_id` varchar(100) DEFAULT NULL,
  `lgbm_score` float DEFAULT NULL,
  `lstm_score` float DEFAULT NULL,
  `hybrid_score` float DEFAULT NULL,
  `status` varchar(50) DEFAULT NULL,
  `reasons` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- Initial Data for Dictionary (Sample)
-- --------------------------------------------------------

INSERT INTO `transaction_dictionary` (`grup`, `jenis_transaksi`, `deskripsi`, `keterangan_remark`) VALUES
('Tarik Tunai', 'ATM BRI', 'Tarik tunai dari ATM/CRM BRI', 'PENARIKAN DARI ATM'),
('Transfer', 'BRImo', 'Transfer sesama BRI via BRImo', 'NBMB'),
('Belanja', 'QRIS', 'Belanja menggunakan QR CPM', 'QRIS'),
('Top Up', 'BRIVA', 'Top UP/bayar via BRIVA', 'BRIVA');

COMMIT;
