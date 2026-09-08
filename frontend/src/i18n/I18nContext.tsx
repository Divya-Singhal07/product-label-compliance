import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

export type Language = 'en' | 'hi'

export type TranslationKey =
  | 'english'
  | 'hindi'
  | 'inspection'
  | 'history'
  | 'dashboard'
  | 'result'
  | 'complianceScore'
  | 'compliant'
  | 'nonCompliant'
  | 'analyzeProduct'
  | 'extractedFields'
  | 'editFields'
  | 'cancel'
  | 'recheckCompliance'
  | 'officerVerified'
  | 'visualVerification'
  | 'detectedLabelFields'
  | 'codesDetected'
  | 'noCodesDetected'
  | 'missingFields'
  | 'warnings'
  | 'ruleDetails'
  | 'downloadPdf'
  | 'scanAnother'
  | 'brand'
  | 'productName'
  | 'genericName'
  | 'netQuantity'
  | 'mrp'
  | 'manufacturer'
  | 'consumerCare'
  | 'countryOfOrigin'
  | 'manufacturingDate'
  | 'status'
  | 'present'
  | 'missing'
  | 'product'
  | 'howItWorks'
  | 'compliance'
  | 'about'
  | 'scanProduct'
  | 'sihLegalMetrology'
  | 'complianceMadeSimple'
  | 'aiPoweredVerification'
  | 'scanAProduct'
  | 'exploreHowItWorks'
  | 'productSection'
  | 'oneLabel'
  | 'dozensDeclarations'
  | 'oneComplianceCheck'
  | 'introBody'
  | 'uploadLabelImages'
  | 'ocrExtractsFields'
  | 'ruleEngineChecks'
  | 'receiveResults'
  | 'scoreYouCanStandBehind'
  | 'complianceExplanation'
  | 'rulesChecked'
  | 'criticalViolations'
  | 'everyDeclaration'
  | 'universal'
  | 'category'
  | 'productLevel'
  | 'readyToCheck'
  | 'startScanning'
  | 'contact'
  | 'scanASproduct'
  | 'readyToAnalyze'
  | 'awaitingAnalysis'
  | 'complianceBreakdown'
  | 'declarationStatus'
  | 'foodChecksNote'
  | 'attention'
  | 'manualReviewRequired'
  | 'notExtracted'
  | 'verificationRecommended'
  | 'officerVerification'
  | 'correctExtractedDeclarations'
  | 'yes'
  | 'no'
  | 'noOcrMatch'
  | 'notVerified'
  | 'barcode'
  | 'noViolationRecords'
  | 'legalReference'
  | 'whyThisMatters'
  | 'howToFix'
  | 'aiFixSuggestion'
  | 'example'
  | 'aiConfidence'
  | 'report'
  | 'backHome'
  | 'front'
  | 'back'
  | 'side'
  | 'uploadInstructions'
  | 'analyzingKeepOpen'
  | 'remove'
  | 'dropLabel'
  | 'browse'
  | 'useCamera'
  | 'retake'
  | 'labelPreview'
  | 'officerDashboard'
  | 'newScan'
  | 'inspectionCommandCenter'
  | 'dashboardHeroCopy'
  | 'scanNewProduct'
  | 'loadingInspectionAnalytics'
  | 'totalInspections'
  | 'allRecordedInspections'
  | 'outcome'
  | 'complianceRate'
  | 'averageConfidence'
  | 'acrossSavedInspections'
  | 'needsAttention'
  | 'totalViolations'
  | 'complianceOverview'
  | 'inspectionOutcomes'
  | 'manualReview'
  | 'activity'
  | 'last7Days'
  | 'ruleAnalysis'
  | 'topViolations'
  | 'noRecordedRuleViolations'
  | 'officerWorkload'
  | 'attentionQueue'
  | 'inspectionsRequiringAttention'
  | 'rulesTriggeredAcrossRecords'
  | 'viewInspectionHistory'
  | 'activityLog'
  | 'recentInspections'
  | 'viewAll'
  | 'noInspectionsYet'
  | 'date'
  | 'score'
  | 'startNewInspection'
  | 'scanFrontBackSideLabels'
  | 'reviewInspectionHistory'
  | 'browsePreviouslyRecordedProducts'
  | 'inspectionRecord'
  | 'productInspection'
  | 'inspectionHistory'
  | 'previousInspections'
  | 'loadingHistory'
  | 'completedInspectionsAppear'
  | 'net'
  | 'scoreLabel'
  | 'cameraCapture'
  | 'cameraClose'
  | 'cameraBack'
  | 'alignLabel'
  | 'goodToScan'
  | 'improveImageQuality'
  | 'cameraPermissionDenied'
  | 'cameraAccessFailed'
  | 'cameraApiUnavailable'
  | 'captureFrameFailed'
  | 'captureImageFailed'
  | 'captureLabel'
  | 'qualityUnableToEvaluate'
  | 'qualityBlurry'
  | 'qualityTooDark'
  | 'qualityTooBright'
  | 'qualityGlare'
  | 'qualityLowContrast'
  | 'qualityChecking'
  | 'captureAnyway'
  | 'captureAnywayHint'

const translations: Record<Language, Record<TranslationKey, string>> = {
  en: {
    english: 'English',
    hindi: 'हिन्दी',
    inspection: 'Inspection',
    history: 'History',
    dashboard: 'Dashboard',
    result: 'Result',
    complianceScore: 'COMPLIANCE SCORE',
    compliant: 'COMPLIANT',
    nonCompliant: 'NON-COMPLIANT',
    analyzeProduct: 'ANALYZE PRODUCT →',
    extractedFields: 'Extracted fields',
    editFields: 'EDIT FIELDS',
    cancel: 'CANCEL',
    recheckCompliance: 'RE-CHECK COMPLIANCE →',
    officerVerified: '✓ Officer verified',
    visualVerification: 'Visual verification',
    detectedLabelFields: 'Detected label fields',
    codesDetected: 'Codes Detected',
    noCodesDetected: 'No QR codes or barcodes detected.',
    missingFields: 'Missing fields',
    warnings: 'Warnings',
    ruleDetails: 'Rule details',
    downloadPdf: 'DOWNLOAD PDF →',
    scanAnother: 'SCAN ANOTHER',
    brand: 'Brand',
    productName: 'Product Name',
    genericName: 'Generic Name',
    netQuantity: 'Net Quantity',
    mrp: 'MRP',
    manufacturer: 'Manufacturer',
    consumerCare: 'Consumer Care',
    countryOfOrigin: 'Country of Origin',
    manufacturingDate: 'Manufacturing Date',
    status: 'Status',
    present: 'PRESENT',
    missing: 'MISSING',
    product: 'Product',
    howItWorks: 'How it Works',
    compliance: 'Compliance',
    about: 'About',
    scanProduct: 'Scan Product',
    sihLegalMetrology: 'SIH26034 · Legal Metrology',
    complianceMadeSimple: 'COMPLIANCE,',
    aiPoweredVerification: 'AI-powered packaged commodity label verification.',
    scanAProduct: 'SCAN A PRODUCT →',
    exploreHowItWorks: 'EXPLORE HOW IT WORKS',
    productSection: '01 — Product',
    oneLabel: 'One label.',
    dozensDeclarations: 'Dozens of declarations.',
    oneComplianceCheck: 'One compliance check.',
    introBody: 'Packaged commodities in India must declare identity, quantity, price, manufacturer, consumer care, origin and date marking. Label Lens reads the pack and screens it against Legal Metrology (Packaged Commodities) Rules, 2011.',
    uploadLabelImages: 'Upload front, back and side label images.',
    ocrExtractsFields: 'OCR extracts relevant declaration fields.',
    ruleEngineChecks: 'The compliance rule engine checks applicable rules.',
    receiveResults: 'Receive a compliance score, violations, warnings and recommendations.',
    scoreYouCanStandBehind: 'A score you can stand behind.',
    complianceExplanation: 'Compliant means no high-severity violations. Medium and low findings still surface for review. Manual review flags low-confidence reads.',
    rulesChecked: 'Rules checked',
    criticalViolations: 'Critical violations',
    everyDeclaration: 'Every declaration, in one reading.',
    universal: 'Universal.',
    category: 'Category.',
    productLevel: 'Product.',
    readyToCheck: 'READY TO CHECK YOUR PRODUCT?',
    startScanning: 'START SCANNING →',
    contact: 'Contact',
    scanASproduct: 'Scan a product',
    readyToAnalyze: 'Ready to analyze.',
    awaitingAnalysis: 'AWAITING ANALYSIS',
    complianceBreakdown: 'Compliance breakdown',
    declarationStatus: 'Declaration status',
    foodChecksNote: 'Food-specific checks may also apply',
    attention: 'Attention',
    manualReviewRequired: 'Manual Review Required',
    notExtracted: 'Not extracted',
    verificationRecommended: 'Verification recommended',
    officerVerification: 'Officer verification',
    correctExtractedDeclarations: 'Correct extracted declarations',
    yes: 'Yes',
    no: 'No',
    noOcrMatch: 'No OCR Match',
    notVerified: 'Not Verified',
    barcode: 'BARCODE',
    noViolationRecords: 'No Violation records to display.',
    legalReference: 'Legal Reference',
    whyThisMatters: 'Why this matters',
    howToFix: 'How to fix',
    aiFixSuggestion: 'AI Fix Suggestion',
    example: 'Example:',
    aiConfidence: 'AI Confidence:',
    report: 'Report',
    backHome: '← Home',
    front: 'Front',
    back: 'Back',
    side: 'Side',
    uploadInstructions: 'Upload front, back and optional side images. The backend will run OCR extraction and compliance checking automatically.',
    analyzingKeepOpen: 'Analyzing… Keep this tab open.',
    remove: 'Remove',
    dropLabel: 'Drop label',
    browse: 'Browse',
    useCamera: '📷 Use Camera',
    retake: 'Retake',
    labelPreview: 'label preview',
    officerDashboard: 'Officer Dashboard',
    newScan: 'New Scan',
    inspectionCommandCenter: 'Inspection Command Center',
    dashboardHeroCopy: 'A live overview of product inspections, compliance outcomes and review workload.',
    scanNewProduct: 'Scan New Product',
    loadingInspectionAnalytics: 'Loading inspection analytics…',
    totalInspections: 'Total inspections',
    allRecordedInspections: 'All recorded inspections',
    outcome: 'Outcome',
    complianceRate: 'Compliance rate',
    averageConfidence: 'Average confidence',
    acrossSavedInspections: 'Across saved inspections',
    needsAttention: 'Needs attention',
    totalViolations: 'total violations',
    complianceOverview: 'Compliance overview',
    inspectionOutcomes: 'Inspection outcomes',
    manualReview: 'Manual review',
    activity: 'Activity',
    last7Days: 'Last 7 days',
    ruleAnalysis: 'Rule analysis',
    topViolations: 'Top violations',
    noRecordedRuleViolations: 'No recorded rule violations yet.',
    officerWorkload: 'Officer workload',
    attentionQueue: 'Attention queue',
    inspectionsRequiringAttention: 'Inspections requiring attention',
    rulesTriggeredAcrossRecords: 'Rules triggered across records',
    viewInspectionHistory: 'View inspection history →',
    activityLog: 'Activity log',
    recentInspections: 'Recent inspections',
    viewAll: 'View all →',
    noInspectionsYet: 'No inspections yet. Start your first product scan.',
    date: 'Date',
    score: 'Score',
    startNewInspection: 'Start a new inspection',
    scanFrontBackSideLabels: 'Scan front, back and side labels',
    reviewInspectionHistory: 'Review inspection history',
    browsePreviouslyRecordedProducts: 'Browse previously recorded products',
    inspectionRecord: 'Inspection record',
    productInspection: 'Product inspection',
    inspectionHistory: 'Inspection History',
    previousInspections: 'Previous product inspections recorded for your account.',
    loadingHistory: 'Loading inspection history…',
    completedInspectionsAppear: 'Your completed product inspections will appear here.',
    net: 'Net',
    scoreLabel: 'Score',
    cameraCapture: 'Camera capture',
    cameraClose: 'Close',
    cameraBack: 'Back',
    alignLabel: 'Align the product label inside the frame',
    goodToScan: 'Good to scan',
    improveImageQuality: 'Improve image quality',
    cameraPermissionDenied: 'Camera permission was denied. Please allow camera access and try again.',
    cameraAccessFailed: 'Could not access the camera on this device.',
    cameraApiUnavailable: 'Camera API unavailable',
    captureFrameFailed: 'Could not capture the camera frame.',
    captureImageFailed: 'Could not create the captured image.',
    captureLabel: 'Capture label',
    qualityUnableToEvaluate: 'Unable to evaluate image quality.',
    qualityBlurry: 'Hold steady — image looks blurry.',
    qualityTooDark: 'Too dark — move to better lighting.',
    qualityTooBright: 'Too bright — reduce direct light.',
    qualityGlare: 'Glare detected — tilt the product slightly.',
    qualityLowContrast: 'Low contrast — improve lighting or avoid shadows.',
    qualityChecking: 'Checking image quality…',
    captureAnyway: 'Capture anyway?',
    captureAnywayHint: 'Quality is not ideal — capture only if the label is readable.',
  },

  hi: {
    english: 'English',
  
    cameraClose: 'बंद करें',
    cameraBack: 'वापस',
    alignLabel: 'उत्पाद के लेबल को फ्रेम के अंदर रखें',
    goodToScan: 'स्कैन करने के लिए तैयार',
    improveImageQuality: 'छवि की गुणवत्ता सुधारें',
    cameraPermissionDenied: 'कैमरा अनुमति अस्वीकार कर दी गई। कृपया कैमरा एक्सेस की अनुमति दें और फिर प्रयास करें।',
    cameraAccessFailed: 'इस डिवाइस पर कैमरा एक्सेस नहीं किया जा सका।',
    cameraApiUnavailable: 'कैमरा API उपलब्ध नहीं है',
    captureFrameFailed: 'कैमरा फ्रेम कैप्चर नहीं किया जा सका।',
    captureImageFailed: 'कैप्चर की गई छवि बनाई नहीं जा सकी।',
    hindi: 'हिन्दी',
    captureLabel: 'लेबल कैप्चर करें',
    qualityUnableToEvaluate: 'छवि गुणवत्ता का मूल्यांकन नहीं किया जा सका।',
    qualityBlurry: 'स्थिर रखें — छवि धुंधली लग रही है।',
    qualityTooDark: 'बहुत अंधेरा है — बेहतर रोशनी में जाएं।',
    qualityTooBright: 'बहुत चमकदार है — सीधी रोशनी कम करें।',
    qualityGlare: 'चमक का पता चला — उत्पाद को थोड़ा झुकाएं।',
    qualityLowContrast: 'कम कंट्रास्ट — रोशनी सुधारें या छाया से बचें।',
    qualityChecking: 'छवि गुणवत्ता जांची जा रही है…',
    captureAnyway: 'फिर भी कैप्चर करें?',
    captureAnywayHint: 'गुणवत्ता आदर्श नहीं है — केवल तभी कैप्चर करें जब लेबल पढ़ने योग्य हो।',
    inspection: 'निरीक्षण',
    history: 'इतिहास',
    dashboard: 'डैशबोर्ड',
    result: 'परिणाम',
    complianceScore: 'अनुपालन स्कोर',
    compliant: 'अनुपालन योग्य',
    nonCompliant: 'अनुपालन योग्य नहीं',
    analyzeProduct: 'उत्पाद का विश्लेषण करें →',
    extractedFields: 'निकाले गए फ़ील्ड',
    editFields: 'फ़ील्ड संपादित करें',
    cancel: 'रद्द करें',
    recheckCompliance: 'अनुपालन पुनः जाँचें →',
    officerVerified: '✓ अधिकारी द्वारा सत्यापित',
    visualVerification: 'दृश्य सत्यापन',
    detectedLabelFields: 'पहचाने गए लेबल फ़ील्ड',
    codesDetected: 'कोड पाए गए',
    noCodesDetected: 'कोई QR कोड या बारकोड नहीं मिला।',
    missingFields: 'अनुपस्थित फ़ील्ड',
    warnings: 'चेतावनियाँ',
    ruleDetails: 'नियम विवरण',
    downloadPdf: 'PDF डाउनलोड करें →',
    scanAnother: 'दूसरा स्कैन करें',
    brand: 'ब्रांड',
    productName: 'उत्पाद का नाम',
    genericName: 'सामान्य नाम',
    netQuantity: 'शुद्ध मात्रा',
    mrp: 'अधिकतम खुदरा मूल्य (MRP)',
    manufacturer: 'निर्माता',
    consumerCare: 'उपभोक्ता सेवा',
    countryOfOrigin: 'मूल देश',
    manufacturingDate: 'निर्माण तिथि',
    status: 'स्थिति',
    present: 'उपस्थित',
    missing: 'अनुपस्थित',
    product: 'उत्पाद',
    howItWorks: 'कैसे काम करता है',
    compliance: 'अनुपालन',
    about: 'हमारे बारे में',
    scanProduct: 'उत्पाद स्कैन करें',
    sihLegalMetrology: 'SIH26034 · विधिक मापविज्ञान',
    complianceMadeSimple: 'अनुपालन,',
    aiPoweredVerification: 'AI आधारित पैकेज्ड कमोडिटी लेबल सत्यापन।',
    scanAProduct: 'उत्पाद स्कैन करें →',
    exploreHowItWorks: 'यह कैसे काम करता है देखें',
    productSection: '01 — उत्पाद',
    oneLabel: 'एक लेबल।',
    dozensDeclarations: 'दर्जनों घोषणाएँ।',
    oneComplianceCheck: 'एक अनुपालन जाँच।',
    introBody: 'भारत में पैकेज्ड कमोडिटी पर पहचान, मात्रा, मूल्य, निर्माता, उपभोक्ता सेवा, मूल देश और तिथि संबंधी घोषणाएँ आवश्यक हो सकती हैं। Label Lens पैकेज को पढ़कर इसे Legal Metrology (Packaged Commodities) Rules, 2011 के अनुसार जाँचता है।',
    uploadLabelImages: 'सामने, पीछे और साइड के लेबल की तस्वीरें अपलोड करें।',
    ocrExtractsFields: 'OCR आवश्यक घोषणा फ़ील्ड निकालता है।',
    ruleEngineChecks: 'अनुपालन नियम इंजन लागू नियमों की जाँच करता है।',
    receiveResults: 'अनुपालन स्कोर, उल्लंघन, चेतावनियाँ और सुझाव प्राप्त करें।',
    scoreYouCanStandBehind: 'एक ऐसा स्कोर जिस पर आप भरोसा कर सकते हैं।',
    complianceExplanation: 'अनुपालन का अर्थ है कि कोई उच्च-गंभीरता वाला उल्लंघन नहीं है। मध्यम और कम स्तर की समस्याएँ समीक्षा के लिए दिखाई जाती हैं। कम विश्वास वाले OCR परिणामों के लिए मैनुअल समीक्षा आवश्यक होती है।',
    rulesChecked: 'जाँचे गए नियम',
    criticalViolations: 'गंभीर उल्लंघन',
    everyDeclaration: 'हर घोषणा, एक ही रीडिंग में।',
    universal: 'सार्वभौमिक।',
    category: 'श्रेणी।',
    productLevel: 'उत्पाद।',
    readyToCheck: 'अपने उत्पाद की जाँच के लिए तैयार हैं?',
    startScanning: 'स्कैन शुरू करें →',
    contact: 'संपर्क',
    scanASproduct: 'उत्पाद स्कैन करें',
    readyToAnalyze: 'विश्लेषण के लिए तैयार।',
    awaitingAnalysis: 'विश्लेषण की प्रतीक्षा',
    complianceBreakdown: 'अनुपालन विवरण',
    declarationStatus: 'घोषणा स्थिति',
    foodChecksNote: 'खाद्य-विशिष्ट जाँच भी लागू हो सकती हैं',
    attention: 'ध्यान दें',
    manualReviewRequired: 'मैनुअल समीक्षा आवश्यक',
    notExtracted: 'निकाला नहीं गया',
    verificationRecommended: 'सत्यापन की अनुशंसा',
    officerVerification: 'अधिकारी सत्यापन',
    correctExtractedDeclarations: 'निकाली गई घोषणाओं को सही करें',
    yes: 'हाँ',
    no: 'नहीं',
    noOcrMatch: 'OCR से मेल नहीं',
    notVerified: 'सत्यापित नहीं',
    barcode: 'बारकोड',
    noViolationRecords: 'दिखाने के लिए कोई उल्लंघन रिकॉर्ड नहीं है।',
    legalReference: 'कानूनी संदर्भ',
    whyThisMatters: 'यह क्यों महत्वपूर्ण है',
    howToFix: 'इसे कैसे ठीक करें',
    aiFixSuggestion: 'AI सुधार सुझाव',
    example: 'उदाहरण:',
    aiConfidence: 'AI विश्वास स्तर:',
    report: 'रिपोर्ट',
    backHome: '← होम',
    front: 'सामने',
    back: 'पीछे',
    side: 'साइड',
    uploadInstructions: 'सामने, पीछे और वैकल्पिक साइड की तस्वीरें अपलोड करें। बैकएंड स्वचालित रूप से OCR और अनुपालन जाँच करेगा।',
    analyzingKeepOpen: 'विश्लेषण हो रहा है… यह टैब खुला रखें।',
    remove: 'हटाएँ',
    dropLabel: 'लेबल की तस्वीर यहाँ छोड़ें',
    browse: 'फ़ाइल चुनें',
    useCamera: '📷 कैमरा उपयोग करें',
    retake: 'फिर से लें',
    labelPreview: 'लेबल पूर्वावलोकन',
    officerDashboard: 'अधिकारी डैशबोर्ड',
    newScan: 'नया स्कैन',
    inspectionCommandCenter: 'निरीक्षण कमांड सेंटर',
    dashboardHeroCopy: 'उत्पाद निरीक्षण, अनुपालन परिणाम और समीक्षा कार्यभार का लाइव अवलोकन।',
    scanNewProduct: 'नया उत्पाद स्कैन करें',
    loadingInspectionAnalytics: 'निरीक्षण विश्लेषण लोड हो रहा है…',
    totalInspections: 'कुल निरीक्षण',
    allRecordedInspections: 'सभी दर्ज निरीक्षण',
    outcome: 'परिणाम',
    complianceRate: 'अनुपालन दर',
    averageConfidence: 'औसत विश्वास स्तर',
    acrossSavedInspections: 'सहेजे गए निरीक्षणों में',
    needsAttention: 'ध्यान आवश्यक',
    totalViolations: 'कुल उल्लंघन',
    complianceOverview: 'अनुपालन अवलोकन',
    inspectionOutcomes: 'निरीक्षण परिणाम',
    manualReview: 'मैनुअल समीक्षा',
    activity: 'गतिविधि',
    last7Days: 'पिछले 7 दिन',
    ruleAnalysis: 'नियम विश्लेषण',
    topViolations: 'शीर्ष उल्लंघन',
    noRecordedRuleViolations: 'अभी तक कोई नियम उल्लंघन दर्ज नहीं है।',
    officerWorkload: 'अधिकारी कार्यभार',
    attentionQueue: 'ध्यान सूची',
    inspectionsRequiringAttention: 'ध्यान आवश्यक निरीक्षण',
    rulesTriggeredAcrossRecords: 'सभी रिकॉर्ड में सक्रिय नियम',
    viewInspectionHistory: 'निरीक्षण इतिहास देखें →',
    activityLog: 'गतिविधि लॉग',
    recentInspections: 'हाल के निरीक्षण',
    viewAll: 'सभी देखें →',
    noInspectionsYet: 'अभी तक कोई निरीक्षण नहीं है। अपना पहला उत्पाद स्कैन शुरू करें।',
    date: 'तिथि',
    score: 'स्कोर',
    startNewInspection: 'नया निरीक्षण शुरू करें',
    scanFrontBackSideLabels: 'सामने, पीछे और साइड के लेबल स्कैन करें',
    reviewInspectionHistory: 'निरीक्षण इतिहास देखें',
    browsePreviouslyRecordedProducts: 'पहले दर्ज किए गए उत्पाद देखें',
    inspectionRecord: 'निरीक्षण रिकॉर्ड',
    productInspection: 'उत्पाद निरीक्षण',
    inspectionHistory: 'निरीक्षण इतिहास',
    previousInspections: 'आपके खाते के लिए दर्ज पिछले उत्पाद निरीक्षण।',
    loadingHistory: 'निरीक्षण इतिहास लोड हो रहा है…',
    completedInspectionsAppear: 'आपके पूरे किए गए उत्पाद निरीक्षण यहाँ दिखाई देंगे।',
    net: 'शुद्ध',
    scoreLabel: 'स्कोर',
    cameraCapture: 'कैमरा कैप्चर',
  },
}

interface I18nContextValue {
  language: Language
  setLanguage: (language: Language) => void
  t: (key: TranslationKey) => string
}

const I18nContext = createContext<I18nContextValue | null>(null)

function getInitialLanguage(): Language {
  const saved = localStorage.getItem('label-lens-language')
  return saved === 'hi' ? 'hi' : 'en'
}

export function I18nProvider({
  children,
}: {
  children: ReactNode
}) {
  const [language, setLanguageState] =
    useState<Language>(getInitialLanguage)

  function setLanguage(language: Language) {
    setLanguageState(language)
    localStorage.setItem('label-lens-language', language)
  }

  const value = useMemo<I18nContextValue>(
    () => ({
      language,
      setLanguage,
      t: (key) => translations[language][key],
    }),
    [language],
  )

  return (
    <I18nContext.Provider value={value}>
      {children}
    </I18nContext.Provider>
  )
}

export function useI18n() {
  const context = useContext(I18nContext)

  if (!context) {
    throw new Error(
      'useI18n must be used inside I18nProvider',
    )
  }

  return context
}
