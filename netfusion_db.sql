-- phpMyAdmin SQL Dump
-- version 5.2.0
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Jun 10, 2026 at 02:27 AM
-- Server version: 10.4.25-MariaDB
-- PHP Version: 8.1.10

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `netfusion_db`
--

-- --------------------------------------------------------

--
-- Table structure for table `products`
--

CREATE TABLE `products` (
  `id` int(11) NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  `brand` varchar(100) DEFAULT NULL,
  `category` varchar(100) DEFAULT NULL,
  `description` text DEFAULT NULL,
  `price` float DEFAULT NULL,
  `in_stock` tinyint(1) DEFAULT NULL,
  `image_url` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `products`
--

INSERT INTO `products` (`id`, `name`, `brand`, `category`, `description`, `price`, `in_stock`, `image_url`) VALUES
(2, 'ASUS ROG Srtix G16 Core™ i9 RTX™ 5070', 'ASUS', 'Workstations & Laptops', 'ASUS ROG Srtix G16 14th Generation | Intel® Core™ i9  14900HX Processor | 32GB DDR5 Ram | 1TB SSD | NVIDIA® GeForce RTX™ 5070 8GB | 16.0″ WUXGA (1920×1200) IPS Anti-glare Display (165Hz) | 4-Zone RGB Backlit Keyboard | Windows 11 | Eclipse Gray | New', 100000, 1, 'https://laptophouse.pk/wp-content/uploads/2025/08/71zuMSjwDfL._AC_SL1500_-2.jpg'),
(3, 'Dell Pro 15 Essentials PV15250 Intel® Core™ i5 1334U', 'Dell', 'Servers & Data Center', 'DELL Pro 15 essential PV15250 13th Generation | Intel® Core™ i5 1334U Processor | 8GB DDR5 Ram | 512GB SSD | 15.6″ FHD (1920 x 1080) Anti-glare Display | Intel® UHD Graphics | Carbon Black | New', 12120, 1, 'https://laptophouse.pk/wp-content/uploads/2026/02/aa-4012-2471496-181025120216500.webp');

-- --------------------------------------------------------

--
-- Table structure for table `settings`
--

CREATE TABLE `settings` (
  `id` int(11) NOT NULL,
  `vendor_email` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `settings`
--

INSERT INTO `settings` (`id`, `vendor_email`) VALUES
(1, 'nabeelshafqat19@gmail.com');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `full_name` varchar(100) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `hashed_password` varchar(255) DEFAULT NULL,
  `is_admin` tinyint(1) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `full_name`, `email`, `hashed_password`, `is_admin`) VALUES
(1, 'admin', 'admin@netfusion.com', '$2b$12$f76b3gb0rX63Q9DBWUSkuudjm7G9CPzBno6WGG3iabyLj6jY9Lmlm', 1),
(2, 'Testinguser', 'TestingUser@netfusion.com', '$2b$12$aoHnRUWaWOiiZCdAKBptTOjSKSrC/vz5DVJuL8H8wc/ie8ZzmI.lS', 0),
(3, 'test', 'test@test', '$2b$12$X0zAsjSJlGopoBIzxH4jGu8Oeyt3RQZitbSSAsFPDN1LyggiH74Sq', 0);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `products`
--
ALTER TABLE `products`
  ADD PRIMARY KEY (`id`),
  ADD KEY `ix_products_id` (`id`),
  ADD KEY `ix_products_category` (`category`),
  ADD KEY `ix_products_brand` (`brand`),
  ADD KEY `ix_products_name` (`name`);

--
-- Indexes for table `settings`
--
ALTER TABLE `settings`
  ADD PRIMARY KEY (`id`),
  ADD KEY `ix_settings_id` (`id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `ix_users_email` (`email`),
  ADD KEY `ix_users_id` (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `products`
--
ALTER TABLE `products`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `settings`
--
ALTER TABLE `settings`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
